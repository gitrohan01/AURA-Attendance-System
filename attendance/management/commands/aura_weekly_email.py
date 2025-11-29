# attendance/management/commands/aura_weekly_email.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date

from attendance.models import Student, User, Attendance, Session, ClassGroup
from attendance.utils import (
    build_weekly_student_report,
    build_hod_weekly_digest,
    send_email_notification,
)


class Command(BaseCommand):
    help = "Send weekly attendance reports to students + HOD digest"

    def handle(self, *args, **kwargs):
        today = date.today()
        start = today - timedelta(days=7)

        hod_digest = []

        # -------------------------------------------------------
        # STUDENTS WEEKLY REPORT
        # -------------------------------------------------------
        for student in Student.objects.all():
            if not student.email:
                continue

            class_group = student.class_group
            if not class_group:
                continue

            qs = Attendance.objects.filter(
                student=student,
                session__class_group=class_group,
                timestamp__date__range=[start, today]
            )

            present = qs.filter(present=True).count()
            absent = qs.filter(present=False).count()
            total = present + absent
            percentage = round((present / total) * 100, 2) if total else 0

            # Build + Send email
            subject, body = build_weekly_student_report(
                student, class_group, present, absent, total, percentage
            )
            send_email_notification(subject, body, [student.email])

            # Prepare for HOD digest
            if percentage < 60:
                hod_digest.append({
                    "student": student,
                    "class": class_group,
                    "percentage": percentage,
                })

        # -------------------------------------------------------
        # SEND HOD DIGEST
        # -------------------------------------------------------
        hods = User.objects.filter(is_hod=True)
        subject, body = build_hod_weekly_digest(hod_digest)

        for h in hods:
            if h.email:
                send_email_notification(subject, body, [h.email])

        self.stdout.write(self.style.SUCCESS("Weekly reports sent successfully."))
