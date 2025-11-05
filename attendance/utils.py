# attendance/utils.py
from django.db.models import Count, Q
from .models import Session, Attendance

def attendance_percentage(student, class_group, subject, start_date, end_date):
    total_sessions = Session.objects.filter(
        class_group=class_group,
        subject=subject,
        start_time__date__range=(start_date, end_date),
        cancelled=False
    ).count()

    attended = Attendance.objects.filter(
        student=student,
        session__class_group=class_group,
        session__subject=subject,
        present=True,
        session__start_time__date__range=(start_date, end_date)
    ).count()

    if total_sessions == 0:
        return 0
    return round((attended / total_sessions) * 100, 2)
