# attendance/urls.py
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from . import views
from . import hod_views




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

    path("hod/fines/", hod_views.hod_fine_calculator, name="hod_fine_calculator"),
    path("hod/fines/class/<int:class_id>/", hod_views.hod_fine_calculator, name="hod_fine_calculator_class"),


    path("hod/devices/", views.device_status, name="device_status"),

    path("teacher/notify_students/", views.notify_students_redflag, name="notify_students_redflag"),

    # Teacher Reports
    path("teacher/reports/", views.teacher_reports, name="teacher_reports"),
    path("teacher/reports/class/<int:class_id>/", views.teacher_report_class, name="teacher_report_class"),
    path("teacher/reports/subject/<int:subject_id>/", views.teacher_report_subject, name="teacher_report_subject"),
    path("teacher/reports/student/<str:student_id>/", views.teacher_report_student, name="teacher_report_student"),
    path("teacher/reports/monthly/", views.teacher_report_monthly, name="teacher_report_monthly"),
    path("teacher/reports/export/", views.teacher_export_center, name="teacher_export_center"),
    # Export Center
    path("teacher/reports/export/", views.teacher_export_center, name="teacher_export_center"),

# Single class export
    path("teacher/export/class/<int:class_id>/<str:fmt>/", views.export_class, name="export_class"),

# Single subject export
    path("teacher/export/subject/<int:subject_id>/<str:fmt>/", views.export_subject, name="export_subject"),

# Bulk ZIP export
    path("teacher/export/bulk/<str:mode>/", views.bulk_export_zip, name="bulk_export_zip"),



    # Subject Reports
    path("teacher/report/subject/<int:subject_id>/", views.teacher_report_subject, name="teacher_report_subject"),
    path("teacher/report/subject/<int:subject_id>/stats/", views.subject_stats_api, name="subject_stats_api"),

    path("teacher/report/subject/<int:subject_id>/export/csv/", views.export_subject_csv_view, name="export_subject_csv"),
    path("teacher/report/subject/<int:subject_id>/export/xlsx/", views.export_subject_xlsx_view, name="export_subject_xlsx"),
    path("teacher/report/subject/<int:subject_id>/export/pdf/", views.export_subject_pdf_view, name="export_subject_pdf"),

    path("subject/<int:subject_id>/export/pdf/", views.subject_export_pdf, name="subject_export_pdf"),




    # -----------------------------
    # HOD CRUD URLs
    # -----------------------------
    path("hod/students/", hod_views.manage_students, name="hod_manage_students"),
    path("hod/students/add/", hod_views.add_student, name="hod_add_student"),
    path("hod/students/edit/<int:pk>/", hod_views.edit_student, name="hod_edit_student"),
    path("hod/students/delete/<int:pk>/", hod_views.delete_student, name="hod_delete_student"),
    path("hod/students/import/", hod_views.import_students, name="hod_import_students"),

    path("hod/teachers/", hod_views.manage_teachers, name="hod_manage_teachers"),
    path("hod/teachers/add/", hod_views.add_teacher, name="hod_add_teacher"),
    path("hod/teachers/edit/<int:pk>/", hod_views.edit_teacher, name="hod_edit_teacher"),
    path("hod/teachers/delete/<int:pk>/", hod_views.delete_teacher, name="hod_delete_teacher"),

    path("hod/classes/", hod_views.manage_classes, name="hod_manage_classes"),
    path("hod/classes/add/", hod_views.add_class, name="hod_add_class"),
    path("hod/classes/edit/<int:pk>/", hod_views.edit_class, name="hod_edit_class"),
    path("hod/classes/delete/<int:pk>/", hod_views.delete_class, name="hod_delete_class"),

    path("hod/subjects/", hod_views.manage_subjects, name="hod_manage_subjects"),
    path("hod/subjects/add/", hod_views.add_subject, name="hod_add_subject"),
    path("hod/subjects/edit/<int:pk>/", hod_views.edit_subject, name="hod_edit_subject"),
    path("hod/subjects/delete/<int:pk>/", hod_views.delete_subject, name="hod_delete_subject"),

# Chart API for HOD → teacher view
path(
    "api/hod/teacher/<int:teacher_id>/weekly/",
    views.hod_teacher_weekly_stats,
    name="hod_teacher_weekly_stats"
),



# -----------------------------
# HOD - Department CRUD
# -----------------------------
path("hod/departments/", hod_views.manage_departments, name="hod_manage_departments"),
path("hod/departments/add/", hod_views.add_department, name="hod_add_department"),
path("hod/departments/edit/<int:pk>/", hod_views.edit_department, name="hod_edit_department"),
path("hod/departments/delete/<int:pk>/", hod_views.delete_department, name="hod_delete_department"),


# -----------------------------
# HOD Analytics Endpoints (JSON)
# -----------------------------
path("hod/analytics/weekly/", hod_views.analytics_weekly, name="hod_analytics_weekly"),
path("hod/analytics/monthly/", hod_views.analytics_monthly, name="hod_analytics_monthly"),
path("hod/analytics/classwise/", hod_views.analytics_classwise, name="hod_analytics_classwise"),
path("hod/analytics/subject_heatmap/", hod_views.analytics_subject_heatmap, name="hod_analytics_subject_heatmap"),
path("hod/analytics/teacher_activity/", hod_views.analytics_teacher_activity, name="hod_analytics_teacher_activity"),
path("hod/analytics/absence_distribution/", hod_views.analytics_absence_distribution, name="hod_analytics_absence_distribution"),

# HOD Analytics Page
path("hod/analytics/", hod_views.hod_analytics_page, name="hod_analytics_page"),

    # -----------------------------
    # HOD PDF REPORTS
    # -----------------------------
    path("hod/report/student/<str:student_id>/pdf/", hod_views.hod_student_report_pdf, name="hod_student_report_pdf"),
    path("hod/report/class/<int:class_id>/pdf/", hod_views.hod_class_report_pdf, name="hod_class_report_pdf"),
    path("hod/report/teacher/<int:teacher_id>/pdf/", hod_views.hod_teacher_report_pdf, name="hod_teacher_report_pdf"),
    path("hod/report/overview/pdf/", hod_views.hod_overview_report_pdf, name="hod_overview_report_pdf"),


path("teacher/pending/", views.teacher_pending_list, name="teacher_pending_list"),
path("teacher/pending/<int:pk>/", views.teacher_pending_review, name="teacher_pending_review"),
path("teacher/pending/<int:pk>/submit/", views.teacher_pending_submit, name="teacher_pending_submit"),

path("logout/", views.logout_view, name="logout"),
]