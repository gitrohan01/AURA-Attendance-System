from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Attendance, Session, Student, TeacherProfile, Subject, ClassGroup
from .serializers import AttendanceSerializer, StudentSerializer, SessionSerializer


# --- GET /api/students/ ---
class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows viewing all registered students (for debugging or IoT sync).
    """
    queryset = Student.objects.all()
    serializer_class = StudentSerializer


# --- POST /api/attendance/ ---
@api_view(['POST'])
def mark_attendance(request):
    """
    ESP32 / IoT devices send attendance data here as JSON.
    Example:
    {
        "student_id": "STU_001",
        "session_id": "S_CS101_20251112_184501",
        "verified_by_face": true,
        "present": true,
        "timestamp": "2025-11-12T18:30:00Z"
    }
    """
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
                status=status.HTTP_400_BAD_REQUEST
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

        return Response(
            {'status': 'success', 'created': created},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- POST /api/start_session/ ---
@api_view(['POST'])
def start_session(request):
    """
    Called when a teacher taps their NFC card.
    Data:
    {
        "teacher_uid": "TCH_001",
        "subject_code": "CS101",
        "class_group": "BCA_2025"
    }
    """
    try:
        teacher_uid = request.data.get('teacher_uid')
        subject_code = request.data.get('subject_code')
        class_name = request.data.get('class_group')

        # Validate teacher
        teacher_profile = TeacherProfile.objects.filter(user__username=teacher_uid).first()
        if not teacher_profile:
            return Response({'status': 'error', 'message': 'Invalid teacher UID'}, status=400)

        subject = Subject.objects.filter(code=subject_code).first()
        class_group = ClassGroup.objects.filter(name=class_name).first()
        if not subject or not class_group:
            return Response({'status': 'error', 'message': 'Invalid subject or class group'}, status=400)

        # Generate unique session ID
        time_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        session_id = f"S_{subject_code}_{time_str}"

        session = Session.objects.create(
            session_id=session_id,
            subject=subject,
            class_group=class_group,
            teacher=teacher_profile.user,
            start_time=timezone.now()
        )

        return Response({'status': 'success', 'session_id': session.session_id}, status=201)

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


# --- POST /api/end_session/ ---
@api_view(['POST'])
def end_session(request):
    """
    Called when teacher taps again to end the class.
    Data:
    {
        "session_id": "S_CS101_20251112_184501"
    }
    """
    try:
        session_id = request.data.get('session_id')
        session = Session.objects.filter(session_id=session_id).first()

        if not session:
            return Response({'status': 'error', 'message': 'Invalid session ID'}, status=400)

        session.end_time = timezone.now()
        session.save()

        return Response({'status': 'success', 'message': 'Session ended'}, status=200)

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)
