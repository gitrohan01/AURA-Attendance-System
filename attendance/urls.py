# attendance/urls.py
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from . import views

# ----- Public Pages -----
def index(request): return render(request, 'attendance/index.html')
def about(request): return render(request, 'attendance/about.html')
def hardware(request): return render(request, 'attendance/hardware.html')
def contact(request): return render(request, 'attendance/contact.html')

# ----- Login -----
def teacher_login(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )
        if user and getattr(user, "is_teacher", False):
            login(request, user)
            return redirect("teacher_dashboard")

        return render(request, "attendance/teacher_login.html", {
            "error": "Invalid credentials or not a Teacher"
        })
    return render(request, "attendance/teacher_login.html")


def hod_login(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )
        if user and getattr(user, "is_hod", False):
            login(request, user)
            return redirect("hod_dashboard")

        return render(request, "attendance/hod_login.html", {
            "error": "Invalid HOD credentials"
        })
    return render(request, "attendance/hod_login.html")


urlpatterns = [
    # Public
    path("", index, name="index"),
    path("about/", about, name="about"),
    path("hardware/", hardware, name="hardware"),
    path("contact/", contact, name="contact"),

    # Login
    path("teacher/login/", teacher_login, name="teacher_login"),
    path("hod/login/", hod_login, name="hod_login"),

    # Teacher
    path("teacher/dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/class/<int:class_id>/", views.teacher_class_detail, name="teacher_class_detail"),
    path("teacher/sessions/", views.teacher_sessions, name="teacher_sessions"),
    path("teacher/redflags/", views.teacher_redflags, name="teacher_redflags"),

    # Export
    path("class/<int:class_id>/export/csv/", views.class_export_csv, name="class_export_csv"),
    path("class/<int:class_id>/export/xlsx/", views.class_export_xlsx, name="class_export_xlsx"),

    path("session/<int:session_id>/export/csv/", views.session_export_csv_view, name="session_export_csv"),
    path("session/<int:session_id>/export/pdf/", views.session_export_pdf_view, name="session_export_pdf"),
    path("session/<int:session_id>/export/xlsx/", views.session_export_xlsx_view, name="session_export_xlsx"),

    # Notify
    path("class/<int:class_id>/notify/", views.notify_hod_class, name="notify_hod_class"),

    # Chart API
    path("api/teacher/weekly/", views.teacher_weekly_stats, name="teacher_weekly_stats"),
    path("api/class/<int:class_id>/weekly/", views.teacher_class_weekly_stats, name="teacher_class_weekly_stats"),
    path("api/hod/department/", views.hod_department_stats, name="hod_department_stats"),

    # HOD
    path("hod/dashboard/", views.hod_dashboard, name="hod_dashboard"),
    path("hod/teacher/<int:teacher_id>/", views.hod_teacher_detail, name="hod_teacher_detail"),

    # HOD: Fine & Devices
    path("hod/fines/", views.fine_calculator, name="hod_fine_calculator"),
    path("hod/fines/class/<int:class_id>/", views.fine_calculator, name="hod_fine_calculator_class"),

    path("hod/devices/", views.device_status, name="device_status"),

    path("teacher/notify_students/", views.notify_students_redflag, name="notify_students_redflag"),

    # Teacher Reports
    path("teacher/reports/", views.teacher_reports, name="teacher_reports"),
    path("teacher/reports/class/<int:class_id>/", views.teacher_report_class, name="teacher_report_class"),
    path("teacher/reports/subject/<int:subject_id>/", views.teacher_report_subject, name="teacher_report_subject"),
    path("teacher/reports/student/<str:student_id>/", views.teacher_report_student, name="teacher_report_student"),
    path("teacher/reports/monthly/", views.teacher_report_monthly, name="teacher_report_monthly"),

    # Subject Reports
    path("teacher/report/subject/<int:subject_id>/", views.teacher_report_subject, name="teacher_report_subject"),
    path("teacher/report/subject/<int:subject_id>/stats/", views.subject_stats_api, name="subject_stats_api"),

    path("teacher/report/subject/<int:subject_id>/export/csv/", views.export_subject_csv_view, name="export_subject_csv"),
    path("teacher/report/subject/<int:subject_id>/export/xlsx/", views.export_subject_xlsx_view, name="export_subject_xlsx"),
    path("teacher/report/subject/<int:subject_id>/export/pdf/", views.export_subject_pdf_view, name="export_subject_pdf"),

    path("subject/<int:subject_id>/export/pdf/", views.subject_export_pdf, name="subject_export_pdf"),
]
