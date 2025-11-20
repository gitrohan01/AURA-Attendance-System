from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import (
    Attendance, Session, Student, TeacherProfile,
    Subject, ClassGroup, Device
)


@api_view(['POST'])
@permission_classes([AllowAny])
def iot_session_upload(request):
    """
    Handles bulk upload from Python Bridge.
    {
        "device_id": "AURA_CLASS_Sigma",
        "session_id": 12345,
        "events": [...]
    }
    """

    data = request.data
    device_id = data.get("device_id")
    sid = data.get("session_id")
    events = data.get("events", [])

    if not device_id or not sid or not events:
        return Response({"status": "error", "message": "Missing fields"}, status=400)

    # ------------------------------------
    # Register or update device heartbeat
    # ------------------------------------
    Device.objects.update_or_create(
        device_id=device_id,
        defaults={
            "name": device_id,
            "last_heartbeat": timezone.now(),
            "meta": {"events_received": len(events)}
        }
    )

    # ------------------------------------
    # Extract teacher UID from session_start
    # ------------------------------------
    teacher_uid = None
    for ev in events:
        if ev.get("type") == "session_start":
            teacher_uid = ev.get("uid")
            break

    if not teacher_uid:
        return Response({"status": "error", "message": "No session_start event found"}, status=400)

    teacher_profile = TeacherProfile.objects.filter(nfc_uid=teacher_uid).first()
    if not teacher_profile:
        return Response({"status": "error", "message": "Invalid teacher card UID"}, status=400)

    teacher = teacher_profile.user
    subject = teacher_profile.subjects.first()
    class_group = teacher_profile.classes.first()

    if not subject or not class_group:
        return Response({"status": "error", "message": "Teacher has no class/subject assigned"}, status=400)

    # ----------------------------------------------------------------
    # CREATE DJANGO SESSION (unique session key)
    # ----------------------------------------------------------------
    session_key = f"S_{subject.code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    s = Session.objects.create(
        session_id=session_key,
        subject=subject,
        class_group=class_group,
        teacher=teacher,
        start_time=timezone.now()
    )

    # ----------------------------------------------------------------
    # EMAIL — SESSION START
    # ----------------------------------------------------------------
    try:
        html_body = render_to_string("attendance/email/session_started.html", {
            "teacher": teacher,
            "subject": subject,
            "class_group": class_group,
            "session": s,
        })
        send_mail(
            subject=f"[AURA] Session Started - {class_group.name}",
            message="",
            html_message=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher.email],
        )
    except Exception as e:
        print("Email error (start):", e)

    # ----------------------------------------------------------------
    # INSERT ATTENDANCE EVENTS
    # ----------------------------------------------------------------
    for ev in events:
        if ev.get("type") != "attendance_mark":
            continue

        uid = ev.get("uid")
        student = Student.objects.filter(nfc_uid=uid).first()
        if not student:
            continue

        Attendance.objects.update_or_create(
            session=s,
            student=student,
            defaults={
                "present": True,
                "verified_by_face": False,
                "timestamp": timezone.now(),
                "source": "IOT",
                "device_id": device_id,
            }
        )

    # ----------------------------------------------------------------
    # END SESSION
    # ----------------------------------------------------------------
    s.end_time = timezone.now()
    s.save()

    # ----------------------------------------------------------------
    # EMAIL — SESSION END
    # ----------------------------------------------------------------
    try:
        html_body = render_to_string("attendance/email/session_ended.html", {
            "teacher": teacher,
            "subject": subject,
            "class_group": class_group,
            "session": s,
            "total": s.attendances.count(),
        })
        send_mail(
            subject=f"[AURA] Session Ended - {class_group.name}",
            message="",
            html_message=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher.email],
        )
    except Exception as e:
        print("Email error (end):", e)

    return Response({
        "status": "success",
        "session": session_key,
        "records": s.attendances.count()
    })
