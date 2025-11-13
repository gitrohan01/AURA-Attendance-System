from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from .models import Attendance, Session, Student
import csv
import io


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
