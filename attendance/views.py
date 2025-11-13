from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from datetime import date, timedelta
import datetime

from .models import (
    User, ClassGroup, Session, Student,
    Department, Attendance, FineRule, Device
)

from .utils import (
    attendance_percentage, send_email_notification,
    export_class_csv, export_session_csv, export_session_pdf,
    export_class_xlsx, export_session_xlsx
)
from django.contrib.auth import authenticate, login

def teacher_login(request):
    next_page = request.GET.get("next", "/teacher/dashboard/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_page = request.POST.get("next", "/teacher/dashboard/")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_teacher:
                login(request, user)
                return redirect(next_page)
            else:
                return render(request, "attendance/teacher_login.html",
                              {"error": "You are not a teacher!"})

        return render(request, "attendance/teacher_login.html",
                      {"error": "Invalid username or password"})

    return render(request, "attendance/teacher_login.html",
                  {"next": next_page})

# -------------------------------------------------------------------
#   Permissions
# -------------------------------------------------------------------
def is_teacher(user):
    return user.is_authenticated and getattr(user, "is_teacher", False)

def is_hod(user):
    return user.is_authenticated and getattr(user, "is_hod", False)

# -------------------------------------------------------------------
#   Teacher Dashboard
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    profile = request.user.teacher_profile
    classes = profile.classes.all()
    subjects = profile.subjects.all()

    return render(request, "attendance/teacher_dashboard.html", {
        "classes": classes,
        "subjects": subjects,
    })

# -------------------------------------------------------------------
#   Teacher Class Detail
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def teacher_class_detail(request, class_id):
    class_group = get_object_or_404(ClassGroup, id=class_id)
    teacher = request.user

    sessions = Session.objects.filter(
        class_group=class_group, teacher=teacher
    ).order_by("-start_time")

    # Weekly summary
    start = date.today() - timedelta(days=7)
    end = date.today()
    students = Student.objects.filter(class_group=class_group)

    summary = []
    for s in students:
        perc = attendance_percentage(s, class_group, None, start, end)
        summary.append({"student": s, "percentage": perc})

    return render(request, "attendance/teacher_class_detail.html", {
        "class_group": class_group,
        "sessions": sessions,
        "summary": summary,
    })

# -------------------------------------------------------------------
#   HOD Dashboard
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_hod)
def hod_dashboard(request):
    teachers = User.objects.filter(is_teacher=True)
    return render(request, "attendance/hod_dashboard.html", {"teachers": teachers})

# -------------------------------------------------------------------
#   HOD → Teacher Detail
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_hod)
def hod_teacher_detail(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id)
    sessions = Session.objects.filter(teacher=teacher)

    return render(request, "attendance/hod_teacher_detail.html", {
        "teacher": teacher,
        "sessions": sessions,
    })

# -------------------------------------------------------------------
#   Chart.js → Teacher Weekly Stats
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def teacher_weekly_stats(request):
    today = date.today()
    labels, present, absent = [], [], []

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%a %d"))

        present.append(Attendance.objects.filter(
            present=True,
            timestamp__date=d,
            session__teacher=request.user
        ).count())

        absent.append(Attendance.objects.filter(
            present=False,
            timestamp__date=d,
            session__teacher=request.user
        ).count())

    return JsonResponse({"labels": labels, "present": present, "absent": absent})

# -------------------------------------------------------------------
#   Chart.js → Class Weekly Stats
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def teacher_class_weekly_stats(request, class_id):
    today = date.today()
    labels, present, absent = [], [], []

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%a %d"))

        present.append(Attendance.objects.filter(
            session__class_group_id=class_id,
            present=True,
            timestamp__date=d
        ).count())

        absent.append(Attendance.objects.filter(
            session__class_group_id=class_id,
            present=False,
            timestamp__date=d
        ).count())

    return JsonResponse({"labels": labels, "present": present, "absent": absent})

# -------------------------------------------------------------------
#   HOD → Department Stats
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_hod)
def hod_department_stats(request):
    thirty = date.today() - timedelta(days=30)
    labels, values = [], []

    for dept in Department.objects.all():
        labels.append(dept.name)

        total_sessions = Session.objects.filter(
            class_group__department=dept,
            start_time__date__gte=thirty
        ).count()

        total_att = Attendance.objects.filter(
            session__class_group__department=dept,
            timestamp__date__gte=thirty
        ).count()

        avg = (total_att / total_sessions) if total_sessions else 0
        values.append(round(avg, 2))

    return JsonResponse({"labels": labels, "values": values})

# -------------------------------------------------------------------
#   Export → Class CSV
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def class_export_csv(request, class_id):
    csv_buf = export_class_csv(class_id)
    response = HttpResponse(csv_buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="class_{class_id}.csv"'
    return response

# -------------------------------------------------------------------
#   Export → Session CSV/PDF
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def session_export_csv_view(request, session_id):
    csv_buf = export_session_csv(session_id)
    response = HttpResponse(csv_buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="session_{session_id}.csv"'
    return response

@login_required
@user_passes_test(is_teacher)
def session_export_pdf_view(request, session_id):
    pdf_bytes = export_session_pdf(session_id)
    return HttpResponse(pdf_bytes, content_type="application/pdf")

# -------------------------------------------------------------------
#   Export → XLSX
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_teacher)
def class_export_xlsx(request, class_id):
    bio = export_class_xlsx(class_id)
    response = HttpResponse(
        bio.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="class_{class_id}.xlsx"'
    return response

@login_required
@user_passes_test(is_teacher)
def session_export_xlsx_view(request, session_id):
    bio = export_session_xlsx(session_id)
    response = HttpResponse(
        bio.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="session_{session_id}.xlsx"'
    return response

# -------------------------------------------------------------------
#   Notify HOD via Email
# -------------------------------------------------------------------
@require_POST
@login_required
@user_passes_test(is_teacher)
def notify_hod_class(request, class_id):
    class_group = get_object_or_404(ClassGroup, id=class_id)
    hods = User.objects.filter(is_hod=True)

    subject = f"[AURA] Attendance Upload - {class_group.name}"
    body = f"""
        Attendance for <b>{class_group.name}</b> has been uploaded.<br>
        Uploaded by: <b>{request.user.username}</b>
    """

    for h in hods:
        if h.email:
            send_email_notification(subject, body, [h.email])

    return JsonResponse({"status": "ok"})

# -------------------------------------------------------------------
#   HOD Fine Calculator
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_hod)
def fine_calculator(request, class_id=None):
    rules = FineRule.objects.filter(active=True).order_by('-id')
    selected_rule = rules.first() if rules.exists() else None

    students = []
    applied_rule = None

    if request.method == "POST":
        rule_id = request.POST.get("rule_id")
        start = request.POST.get("start_date")
        end = request.POST.get("end_date")

        start = datetime.date.fromisoformat(start) if start else date.today().replace(day=1)
        end = datetime.date.fromisoformat(end) if end else date.today()

        applied_rule = FineRule.objects.filter(id=rule_id).first()

        class_id = request.POST.get("class_id") or class_id
        students_qs = Student.objects.filter(class_group_id=class_id) if class_id else Student.objects.all()

        for s in students_qs:
            perc = attendance_percentage(s, s.class_group, None, start, end)

            total_sessions = Session.objects.filter(
                class_group=s.class_group,
                start_time__date__range=(start, end),
                cancelled=False
            ).count()

            present_count = Attendance.objects.filter(
                student=s, present=True,
                session__start_time__date__range=(start, end)
            ).count()

            absent_days = total_sessions - present_count
            fine = float(applied_rule.fine_per_day) * absent_days if applied_rule and perc < applied_rule.threshold_percent else 0

            students.append({
                "student": s,
                "percentage": perc,
                "absent_days": absent_days,
                "fine": fine
            })

    return render(request, "attendance/hod_fine_calculator.html", {
        "rules": rules,
        "selected_rule": selected_rule,
        "students": students,
        "applied_rule": applied_rule,
    })

# -------------------------------------------------------------------
#   Device Status
# -------------------------------------------------------------------
@login_required
@user_passes_test(is_hod)
def device_status(request):
    devices = Device.objects.all().order_by('-last_heartbeat')
    return render(request, "attendance/device_status.html", {"devices": devices})
