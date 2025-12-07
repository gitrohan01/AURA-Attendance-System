# attendance/api_views_iot.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from .models import (
    Student, TeacherProfile, Subject, ClassGroup,
    PendingSession, PendingStudent
)

@api_view(['POST'])
@permission_classes([AllowAny])
def iot_session_upload(request):
    """
    IoT → Python Bridge → Django
    {
        "device_id": "AURA_CLASS_1",
        "session_id": 3,
        "events": [
           {"type":"session_start","uid":"TEACHER_UID"},
           {"type":"attendance_mark","uid":"STUDENT_UID"},
           {"type":"session_end","uid":"TEACHER_UID"}
        ]
    }
    """

    data = request.data
    device_id = data.get("device_id")
    events = data.get("events", [])

    if not device_id or not events:
        return Response({"status": "error", "msg": "Missing fields"}, status=400)

    # -------------------------------
    # Find teacher UID from events
    # -------------------------------
    teacher_uid = None
    for ev in events:
        if ev.get("type") == "session_start":
            teacher_uid = ev.get("uid")
            break

    if not teacher_uid:
        return Response({"status": "error", "msg": "No session_start"}, status=400)

    teacher_profile = TeacherProfile.objects.filter(nfc_uid=teacher_uid).first()
    if not teacher_profile:
        return Response({"status": "error", "msg": "Invalid teacher card"}, status=400)

    teacher = teacher_profile.user
    subject = teacher_profile.subjects.first()
    class_group = teacher_profile.classes.first()

    if not subject or not class_group:
        return Response({"status": "error", "msg": "Teacher has no subject/class assigned"}, status=400)

    # -------------------------------------
    # Create PendingSession
    # -------------------------------------
    temp_id = f"IOT_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
    pending = PendingSession.objects.create(
        temp_id=temp_id,
        teacher=teacher,
        subject=subject,
        class_group=class_group,
        device_id=device_id,
    )

    # -------------------------------------
    # Create PendingStudent entries
    # -------------------------------------
    for ev in events:
        if ev.get("type") != "attendance_mark":
            continue

        uid = ev.get("uid")
        student = Student.objects.filter(nfc_uid=uid).first()
        if not student:
            continue

        PendingStudent.objects.create(
            pending_session=pending,
            student=student,
            present=True,
            timestamp=timezone.now()
        )

    return Response({
        "status": "success",
        "pending_session": pending.temp_id,
        "students": PendingStudent.objects.filter(pending_session=pending).count()
    })
