from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from .models import Attendance, Session, Student
import csv
import io

from weasyprint import HTML
from django.template.loader import render_to_string
import csv, io
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from attendance.models import Session, Attendance 

# new imports for xlsx
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import datetime
from io import BytesIO

# -------------------------------------------------------------------
#   Attendance Percentage
# -------------------------------------------------------------------
def attendance_percentage(student, class_group, subject, start_date, end_date):
    total = Attendance.objects.filter(
        student=student,
        session__class_group=class_group,
        session__start_time__date__range=(start_date, end_date)
    ).count()

    present = Attendance.objects.filter(
        student=student,
        session__class_group=class_group,
        present=True,
        session__start_time__date__range=(start_date, end_date)
    ).count()

    if total == 0:
        return 0

    return round((present / total) * 100, 2)

# -------------------------------------------------------------------
#   Email Notification
# -------------------------------------------------------------------
def send_email_notification(subject, body, recipients):
    try:
        msg = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipients
        )
        msg.content_subtype = "html"
        msg.send()
    except Exception as e:
        print("Email error:", e)

# -------------------------------------------------------------------
#   Export → Class CSV
# -------------------------------------------------------------------
def export_class_csv(class_id):
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow(["student_id", "name", "present", "timestamp"])

    attendances = Attendance.objects.filter(
        session__class_group_id=class_id
    ).select_related("student")

    for a in attendances:
        w.writerow([
            a.student.student_id,
            f"{a.student.first_name} {a.student.last_name}",
            "Present" if a.present else "Absent",
            a.timestamp
        ])

    buf.seek(0)
    return buf

# -------------------------------------------------------------------
#   Export → Session CSV
# -------------------------------------------------------------------
def export_session_csv(session_id):
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow(["student_id", "name", "present", "timestamp"])

    attendances = Attendance.objects.filter(
        session_id=session_id
    ).select_related("student")

    for a in attendances:
        w.writerow([
            a.student.student_id,
            f"{a.student.first_name} {a.student.last_name}",
            "Present" if a.present else "Absent",
            a.timestamp
        ])

    buf.seek(0)
    return buf

# -------------------------------------------------------------------
#   Export → Session PDF (WeasyPrint)
# -------------------------------------------------------------------
def export_session_pdf(session_id):
    from weasyprint import HTML
    session = Session.objects.filter(id=session_id).first()
    attendances = Attendance.objects.filter(session=session).select_related("student")

    html = render_to_string("attendance/pdf/session_report.html", {
        "session": session,
        "attendances": attendances
    })

    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes

# -------------------------------------------------------------------
#   Export → Class XLSX (openpyxl)
# -------------------------------------------------------------------
def export_class_xlsx(class_id):
    attendances = Attendance.objects.filter(session__class_group_id=class_id).select_related('student','session')
    wb = Workbook()
    ws = wb.active
    ws.title = f"Class_{class_id}_Attendance"

    headers = ["Session ID","Student ID","Student Name","Present","Verified By Face","Timestamp","Source"]
    ws.append(headers)

    for a in attendances.order_by('session__start_time','timestamp'):
        ws.append([
            a.session.session_id,
            a.student.student_id,
            f"{a.student.first_name} {a.student.last_name}",
            "Yes" if a.present else "No",
            "Yes" if a.verified_by_face else "No",
            a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            a.source
        ])

    # Auto-width
    for i, col in enumerate(ws.columns, 1):
        max_length = max((len(str(cell.value)) if cell.value else 0) for cell in col)
        ws.column_dimensions[get_column_letter(i)].width = min(max_length + 4, 50)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio

# -------------------------------------------------------------------
#   Export → Session XLSX
# -------------------------------------------------------------------
def export_session_xlsx(session_id):
    attendances = Attendance.objects.filter(session_id=session_id).select_related('student')
    wb = Workbook()
    ws = wb.active
    ws.title = f"Session_{session_id}"

    headers = ["Student ID","Student Name","Present","Verified By Face","Timestamp","Source"]
    ws.append(headers)

    for a in attendances.order_by('timestamp'):
        ws.append([
            a.student.student_id,
            f"{a.student.first_name} {a.student.last_name}",
            "Yes" if a.present else "No",
            "Yes" if a.verified_by_face else "No",
            a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            a.source
        ])

    # auto width
    for i, col in enumerate(ws.columns, 1):
        max_length = max((len(str(cell.value)) if cell.value else 0) for cell in col)
        ws.column_dimensions[get_column_letter(i)].width = min(max_length + 4, 50)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio




# attendance/utils.py  (append)

from datetime import date, timedelta
from django.template.loader import render_to_string

def red_flag_students_for_user(user, days=30, threshold=60):
    """
    Return list of dicts: { 'student': Student, 'class_group': ClassGroup, 'percentage': float }
    For all classes assigned to this teacher (teacher_profile.classes).
    """
    flagged = []
    try:
        classes = user.teacher_profile.classes.all()
    except Exception:
        return flagged

    start = date.today() - timedelta(days=days)
    end = date.today()

    for c in classes:
        students = Student.objects.filter(class_group=c)
        for s in students:
            perc = attendance_percentage(s, c, None, start, end)
            if perc < threshold:
                flagged.append({"student": s, "class_group": c, "percentage": perc})

    return flagged


def render_redflag_email(student, class_group, percentage):
    """
    Simple HTML body for student notification. You can replace with a template.
    """
    subject = f"[AURA] Attendance Alert — {class_group.name}"
    body = render_to_string("attendance/email/redflag_student.html", {
        "student": student,
        "class_group": class_group,
        "percentage": percentage,
        "threshold": 60,
    })
    return subject, body



def export_subject_csv(subject):
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow(["Session ID", "Class", "Start Time", "End Time", "Total Present", "Total Absent"])

    sessions = Session.objects.filter(subject=subject)

    for s in sessions:
        present = Attendance.objects.filter(session=s, present=True).count()
        absent = Attendance.objects.filter(session=s, present=False).count()

        w.writerow([
            s.session_id,
            s.class_group.name,
            s.start_time.strftime("%Y-%m-%d %H:%M"),
            s.end_time.strftime("%Y-%m-%d %H:%M") if s.end_time else "ONGOING",
            present,
            absent
        ])

    buf.seek(0)
    return buf



def export_subject_xlsx(subject):
    sessions = Session.objects.filter(subject=subject)
    wb = Workbook()
    ws = wb.active
    ws.title = f"{subject.code}_Report"

    headers = ["Session ID", "Class", "Start Time", "End Time", "Present", "Absent"]
    ws.append(headers)

    for s in sessions:
        present = Attendance.objects.filter(session=s, present=True).count()
        absent = Attendance.objects.filter(session=s, present=False).count()

        ws.append([
            s.session_id,
            s.class_group.name,
            s.start_time.strftime("%Y-%m-%d %H:%M"),
            s.end_time.strftime("%Y-%m-%d %H:%M") if s.end_time else "ONGOING",
            present,
            absent
        ])

    # Auto width
    for i, col in enumerate(ws.columns, 1):
        max_length = max((len(str(cell.value)) if cell.value else 0) for cell in col)
        ws.column_dimensions[get_column_letter(i)].width = min(max_length + 4, 50)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio




def export_subject_pdf(subject):
    sessions = Session.objects.filter(subject=subject)

    html = render_to_string("attendance/pdf/subject_report.html", {
        "subject": subject,
        "sessions": sessions
    })

    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes




# ------------------ SUBJECT REPORT PDF ----------------------------------
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from io import BytesIO
from django.utils import timezone

from .models import Attendance, Session, Student, Subject


def export_subject_pdf(subject_id):
    subject = Subject.objects.get(id=subject_id)

    sessions = Session.objects.filter(subject=subject)
    total_sessions = sessions.count()

    students = Student.objects.filter(class_group__in=sessions.values("class_group").distinct())

    stats = []

    for s in students:
        present = Attendance.objects.filter(
            student=s, 
            session__in=sessions,
            present=True
        ).count()

        absent = total_sessions - present

        percentage = round((present / total_sessions) * 100, 2) if total_sessions > 0 else 0

        stats.append({
            "student": s,
            "present": present,
            "absent": absent,
            "percentage": percentage
        })

    html = render_to_string("attendance/pdf/subject_report.html", {
        "subject": subject,
        "stats": stats,
        "total_sessions": total_sessions,
        "report_date": timezone.now().date(),
    })

    pdf_file = BytesIO()
    HTML(string=html).write_pdf(pdf_file)

    pdf_file.seek(0)
    return pdf_file



