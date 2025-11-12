from rest_framework import serializers
from .models import Attendance, Session, Student




class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'session_id', 'subject', 'class_group', 'teacher', 'start_time', 'end_time', 'cancelled']

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'student_id', 'first_name', 'last_name', 'class_group']


class AttendanceSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    session = SessionSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'session', 'student', 'timestamp', 'verified_by_face', 'present', 'source']

