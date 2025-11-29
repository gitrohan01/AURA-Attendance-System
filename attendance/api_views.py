from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from .models import (
    Attendance, Session, Student,
    TeacherProfile, Subject, ClassGroup, Device
)
from .serializers import (
    AttendanceSerializer, StudentSerializer, SessionSerializer
)

# Email utilities
from attendance.utils import (
    build_session_start_email,
    build_session_end_email,
    send_email_notification
)


# -------------------------------------------------------------------
#   /api/students/
# -------------------------------------------------------------------
class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer


# -------------------------------------------------------------------
#   /api/attendance/  (mark attendance)
# -------------------------------------------------------------------
@api_view(['POST'])
def mark_attendance(request):
    try:
        student_id = request.data.get('student_id')
        session_id = request.data.get('session_id')
        verified_by_face = request.data.get('verified_by_face', False)
        present = request.data.get('present', True)
        timestamp = request.data.get('timestamp', timezone.now())

        student = Student.objects.filter(student_id=student_id).first()
        session = Session.objects.filter(session_id=session_id).first()

        if not student or not session:
            return Response(
                {'status': 'error', 'message': 'Invalid student or session ID'},
                status=400
            )

        attendance, created = Attendance.objects.update_or_create(
            student=student,
            session=session,
            defaults={
                'verified_by_face': verified_by_face,
                'present': present,
                'timestamp': timestamp,
                'source': 'ESP32'
            }
        )

        return Response({'status': 'success', 'created': created}, status=201)

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


# -------------------------------------------------------------------
#   /api/start_session/
# -------------------------------------------------------------------
@api_view(['POST'])
def start_session(request):
    try:
        teacher_uid = request.data.get('teacher_uid')
        subject_code = request.data.get('subject_code')
        class_name = request.data.get('class_group')

        teacher_profile = TeacherProfile.objects.filter(user__username=teacher_uid).first()
        if not teacher_profile:
            return Response({'status': 'error', 'message': 'Invalid teacher UID'}, status=400)

        subject = Subject.objects.filter(code=subject_code).first()
        class_group = ClassGroup.objects.filter(name=class_name).first()

        if not subject or not class_group:
            return Response({'status': 'error', 'message': 'Invalid subject or class'}, status=400)

        time_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        session_id = f"S_{subject_code}_{time_str}"

        session = Session.objects.create(
            session_id=session_id,
            subject=subject,
            class_group=class_group,
            teacher=teacher_profile.user,
            start_time=timezone.now()
        )

        # ------------------------------
        # SEND EMAIL TO TEACHER
        # ------------------------------
        subject_mail, body_mail = build_session_start_email(session, teacher_profile.user)
        if teacher_profile.user.email:
            send_email_notification(subject_mail, body_mail, [teacher_profile.user.email])

        return Response({'status': 'success', 'session_id': session.session_id}, status=201)

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


# -------------------------------------------------------------------
#   /api/end_session/
# -------------------------------------------------------------------
@api_view(['POST'])
def end_session(request):
    try:
        session_id = request.data.get('session_id')
        session = Session.objects.filter(session_id=session_id).first()

        if not session:
            return Response({'status': 'error', 'message': 'Invalid session ID'}, status=400)

        session.end_time = timezone.now()
        session.save()

        # ------------------------------
        # SEND EMAIL – SESSION SUMMARY
        # ------------------------------
        subject_mail, body_mail = build_session_end_email(session)
        teacher = session.teacher
        if teacher and teacher.email:
            send_email_notification(subject_mail, body_mail, [teacher.email])

        return Response({'status': 'success', 'message': 'Session ended'}, status=200)

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


# -------------------------------------------------------------------
#   /api/heartbeat/  (ESP32 ONLINE/OFFLINE CHECK)
# -------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def device_heartbeat(request):
    """
    IoT Heartbeat:
    {
        "device_id": "ESP32-CLASS2",
        "name": "Class 2 Gate",
        "meta": {"ip":"192.168.1.21"}
    }
    """
    try:
        data = request.data
        device_id = data.get("device_id")

        if not device_id:
            return Response({"status": "error", "message": "device_id required"}, status=400)

        device, created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={"name": data.get("name"), "meta": data.get("meta")}
        )

        device.last_heartbeat = timezone.now()
        device.name = data.get("name", device.name)
        device.meta = data.get("meta", device.meta)
        device.save()

        return Response({"status": "ok", "created": created}, status=200)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)
