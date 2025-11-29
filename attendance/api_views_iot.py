# attendance/api_views_iot.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import get_user_model

from attendance.utils import (
    build_session_start_email,
    build_session_end_email,
    build_teacher_upload_email,
    build_hod_upload_email,
    send_email_notification,
)

from .models import (
    Attendance, Session, Student, TeacherProfile,
    Subject, ClassGroup, Device, User
)


@api_view(['POST'])
@permission_classes([AllowAny])
def iot_session_upload(request):
    """
    IoT → Python Bridge → Django.
    {
        "device_id": "AURA_CLASS",
        "session_id": "ignored_by_django",
        "events": [
           {"type":"session_start", "uid":"TEACHER_UID"},
           {"type":"attendance_mark", "uid":"STUDENT_UID"},
           ...
        ]
    }
    """

    data = request.data
    device_id = data.get("device_id")
    events = data.get("events", [])

    if not device_id or not events:
        return Response({"status": "error", "message": "Missing fields"}, status=400)

    # ---------------------------------------------------------
    # Update device heartbeat
    # ---------------------------------------------------------
    Device.objects.update_or_create(
        device_id=device_id,
        defaults={
            "name": device_id,
            "last_heartbeat": timezone.now(),
            "meta": {"events_received": len(events)},
        }
    )

    # ---------------------------------------------------------
    # Extract teacher UID from session_start
    # ---------------------------------------------------------
    teacher_uid = None
    for ev in events:
        if ev.get("type") == "session_start":
            teacher_uid = ev.get("uid")
            break

    if not teacher_uid:
        return Response({"status": "error", "message": "No session_start event"}, status=400)

    teacher_profile = TeacherProfile.objects.filter(nfc_uid=teacher_uid).first()
    if not teacher_profile:
        return Response({"status": "error", "message": "Invalid teacher card UID"}, status=400)

    teacher = teacher_profile.user
    subject = teacher_profile.subjects.first()
    class_group = teacher_profile.classes.first()

    if not subject or not class_group:
        return Response({"status": "error", "message": "Teacher has no assigned class/subject"}, status=400)

    # ---------------------------------------------------------
    # CREATE DJANGO SESSION (unique)
    # ---------------------------------------------------------
    session_key = f"S_{subject.code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    s = Session.objects.create(
        session_id=session_key,
        subject=subject,
        class_group=class_group,
        teacher=teacher,
        start_time=timezone.now()
    )

    # ---------------------------------------------------------
    # EMAIL — SESSION START (teacher)
    # ---------------------------------------------------------
    try:
        sub, body = build_session_start_email(s, teacher)
        if teacher.email:
            send_email_notification(sub, body, [teacher.email])
    except Exception as e:
        print("Email error (start):", e)

    # ---------------------------------------------------------
    # INSERT ATTENDANCE EVENTS
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # END SESSION
    # ---------------------------------------------------------
    s.end_time = timezone.now()
    s.save()

    # ---------------------------------------------------------
    # EMAIL — SESSION END (teacher)
    # ---------------------------------------------------------
    try:
        sub, body = build_session_end_email(s)
        if teacher.email:
            send_email_notification(sub, body, [teacher.email])
    except Exception as e:
        print("Email error (end):", e)

    # ---------------------------------------------------------
    # EMAIL — TEACHER UPLOAD CONFIRMATION
    # ---------------------------------------------------------
    try:
        sub, body = build_teacher_upload_email(teacher, class_group)
        if teacher.email:
            send_email_notification(sub, body, [teacher.email])
    except Exception as e:
        print("Email error (upload teacher):", e)

    # ---------------------------------------------------------
    # EMAIL — HOD NOTIFY
    # ---------------------------------------------------------
    try:
        hods = User.objects.filter(is_hod=True)
        for h in hods:
            if not h.email:
                continue
            sub, body = build_hod_upload_email(teacher, class_group)
            send_email_notification(sub, body, [h.email])
    except Exception as e:
        print("Email error (notify HOD):", e)

    # ---------------------------------------------------------
    # Final response
    # ---------------------------------------------------------
    return Response({
        "status": "success",
        "session": session_key,
        "records": s.attendances.count()
    })
