# attendance/hod_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now

from weasyprint import HTML

import csv
import io
from datetime import timedelta

from .models import (
    User, Student, ClassGroup, Subject, TeacherProfile,
    Department, Session, Attendance
)
from . import analytics as aura_analytics


# =====================================================
# HELPERS / ACCESS CONTROL
# =====================================================

def _last_30_days():
    """Return (start_date, end_date) for last 30 days."""
    today = now().date()
    start = today - timedelta(days=30)
    return start, today


def is_hod(user):
    return user.is_authenticated and getattr(user, "is_hod", False)


def hod_only(view_func):
    return login_required(user_passes_test(is_hod)(view_func))


# =====================================================
# STUDENT CRUD
# =====================================================

@hod_only
def manage_students(request):
    students = Student.objects.select_related("class_group").order_by("student_id")
    classes = ClassGroup.objects.all().order_by("name")
    return render(request, "attendance/hod_manage_students.html", {
        "students": students,
        "classes": classes,
    })


@hod_only
def add_student(request):
    classes = ClassGroup.objects.all().order_by("name")

    if request.method == "POST":
        student_id = request.POST.get("student_id", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        nfc_uid = request.POST.get("nfc_uid", "").strip()
        class_id = request.POST.get("class_group")

        if not student_id or not first_name:
            messages.error(request, "Student ID and First Name are required.")
            return redirect("hod_add_student")

        Student.objects.create(
            student_id=student_id,
            first_name=first_name,
            last_name=last_name,
            email=email or None,
            nfc_uid=nfc_uid or None,
            class_group_id=class_id or None,
        )

        messages.success(request, f"Student {student_id} created.")
        return redirect("hod_manage_students")

    return render(request, "attendance/hod_add_student.html", {"classes": classes})


@hod_only
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    classes = ClassGroup.objects.all().order_by("name")

    if request.method == "POST":
        student.student_id = request.POST.get("student_id", "").strip()
        student.first_name = request.POST.get("first_name", "").strip()
        student.last_name = request.POST.get("last_name", "").strip()
        student.email = request.POST.get("email", "").strip() or None
        student.nfc_uid = request.POST.get("nfc_uid", "").strip() or None
        student.class_group_id = request.POST.get("class_group") or None

        if not student.student_id or not student.first_name:
            messages.error(request, "Student ID and First Name are required.")
            return redirect("hod_edit_student", pk=pk)

        student.save()
        messages.success(request, f"Student {student.student_id} updated.")
        return redirect("hod_manage_students")

    return render(request, "attendance/hod_edit_student.html", {
        "student": student,
        "classes": classes,
    })


@hod_only
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    sid = student.student_id
    student.delete()
    messages.success(request, f"Student {sid} deleted.")
    return redirect("hod_manage_students")


# =====================================================
# TEACHER CRUD
# =====================================================

@hod_only
def manage_teachers(request):
    teachers = TeacherProfile.objects.select_related("user").prefetch_related("classes", "subjects")
    classes = ClassGroup.objects.all().order_by("name")
    subjects = Subject.objects.all().order_by("code")
    return render(request, "attendance/hod_manage_teachers.html", {
        "teachers": teachers,
        "classes": classes,
        "subjects": subjects,
    })


@hod_only
def add_teacher(request):
    users = User.objects.filter(is_teacher=True).order_by("username")
    classes = ClassGroup.objects.all().order_by("name")
    subjects = Subject.objects.all().order_by("code")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        nfc_uid = request.POST.get("nfc_uid", "").strip()
        class_ids = request.POST.getlist("classes")
        subject_ids = request.POST.getlist("subjects")

        user = get_object_or_404(User, pk=user_id)

        with transaction.atomic():
            profile, created = TeacherProfile.objects.get_or_create(user=user)
            profile.nfc_uid = nfc_uid or None
            profile.save()
            profile.classes.set(class_ids)
            profile.subjects.set(subject_ids)

        messages.success(request, f"Teacher profile for {user.username} saved.")
        return redirect("hod_manage_teachers")

    return render(request, "attendance/hod_add_teacher.html", {
        "users": users,
        "classes": classes,
        "subjects": subjects,
    })


@hod_only
def edit_teacher(request, pk):
    profile = get_object_or_404(TeacherProfile, pk=pk)
    classes = ClassGroup.objects.all().order_by("name")
    subjects = Subject.objects.all().order_by("code")

    if request.method == "POST":
        profile.nfc_uid = request.POST.get("nfc_uid", "").strip() or None
        profile.save()

        profile.classes.set(request.POST.getlist("classes"))
        profile.subjects.set(request.POST.getlist("subjects"))

        messages.success(request, f"Teacher {profile.user.username} updated.")
        return redirect("hod_manage_teachers")

    return render(request, "attendance/hod_edit_teacher.html", {
        "profile": profile,
        "classes": classes,
        "subjects": subjects,
    })


@hod_only
def delete_teacher(request, pk):
    profile = get_object_or_404(TeacherProfile, pk=pk)
    username = profile.user.username
    profile.delete()
    messages.success(request, f"Teacher profile for {username} deleted.")
    return redirect("hod_manage_teachers")


# =====================================================
# CLASS CRUD
# =====================================================

@hod_only
def manage_classes(request):
    classes = ClassGroup.objects.select_related("department").order_by("name")
    return render(request, "attendance/hod_manage_classes.html", {"classes": classes})


@hod_only
def add_class(request):
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        dept_id = request.POST.get("department")

        if not name:
            messages.error(request, "Class name is required.")
            return redirect("hod_add_class")

        ClassGroup.objects.create(
            name=name,
            description=description or "",
            department_id=dept_id or None,
        )

        messages.success(request, f"Class {name} created.")
        return redirect("hod_manage_classes")

    return render(request, "attendance/hod_add_class.html", {
        "departments": departments,
    })


@hod_only
def edit_class(request, pk):
    c = get_object_or_404(ClassGroup, pk=pk)
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        c.name = request.POST.get("name", "").strip()
        c.description = request.POST.get("description", "").strip()
        c.department_id = request.POST.get("department") or None

        if not c.name:
            messages.error(request, "Class name is required.")
            return redirect("hod_edit_class", pk=pk)

        c.save()
        messages.success(request, f"Class {c.name} updated.")
        return redirect("hod_manage_classes")

    return render(request, "attendance/hod_edit_class.html", {
        "class_group": c,
        "departments": departments,
    })


@hod_only
def delete_class(request, pk):
    c = get_object_or_404(ClassGroup, pk=pk)
    name = c.name
    c.delete()
    messages.success(request, f"Class {name} deleted.")
    return redirect("hod_manage_classes")


# =====================================================
# SUBJECT CRUD
# =====================================================

@hod_only
def manage_subjects(request):
    subjects = Subject.objects.select_related("department").order_by("code")
    return render(request, "attendance/hod_manage_subjects.html", {"subjects": subjects})


@hod_only
def add_subject(request):
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        dept_id = request.POST.get("department")

        if not code or not name:
            messages.error(request, "Subject code and name are required.")
            return redirect("hod_add_subject")

        Subject.objects.create(
            code=code,
            name=name,
            department_id=dept_id or None,
        )

        messages.success(request, f"Subject {code} created.")
        return redirect("hod_manage_subjects")

    return render(request, "attendance/hod_add_subject.html", {
        "departments": departments,
    })


@hod_only
def edit_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        subject.code = request.POST.get("code", "").strip()
        subject.name = request.POST.get("name", "").strip()
        subject.department_id = request.POST.get("department") or None

        if not subject.code or not subject.name:
            messages.error(request, "Subject code and name are required.")
            return redirect("hod_edit_subject", pk=pk)

        subject.save()
        messages.success(request, f"Subject {subject.code} updated.")
        return redirect("hod_manage_subjects")

    return render(request, "attendance/hod_edit_subject.html", {
        "subject": subject,
        "departments": departments,
    })


@hod_only
def delete_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    name = subject.code
    subject.delete()
    messages.success(request, f"Subject {name} deleted.")
    return redirect("hod_manage_subjects")


# =====================================================
# BULK IMPORT STUDENTS
# =====================================================

@hod_only
def import_students(request):
    classes = ClassGroup.objects.all().order_by("name")

    if request.method == "POST":
        file = request.FILES.get("csv_file")
        if not file:
            messages.error(request, "Upload a CSV file.")
            return redirect("hod_import_students")

        try:
            decoded = file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
        except Exception as e:
            messages.error(request, f"CSV read error: {e}")
            return redirect("hod_import_students")

        created = 0
        updated = 0

        for row in reader:
            sid = row.get("student_id", "").strip()
            if not sid:
                continue

            class_name = row.get("class_group_name", "").strip()
            class_obj = ClassGroup.objects.filter(name=class_name).first() if class_name else None

            defaults = {
                "first_name": row.get("first_name", "").strip(),
                "last_name": row.get("last_name", "").strip(),
                "email": row.get("email", "").strip() or None,
                "nfc_uid": row.get("nfc_uid", "").strip() or None,
                "class_group": class_obj,
            }

            obj, is_created = Student.objects.update_or_create(
                student_id=sid,
                defaults=defaults,
            )

            if is_created:
                created += 1
            else:
                updated += 1

        messages.success(request, f"Import complete: Created {created}, Updated {updated}")
        return redirect("hod_manage_students")

    return render(request, "attendance/hod_import_students.html", {"classes": classes})


# =====================================================
# DEPARTMENT CRUD
# =====================================================

@hod_only
def manage_departments(request):
    departments = Department.objects.all().order_by("name")
    return render(request, "attendance/hod_manage_departments.html", {
        "departments": departments,
    })


@hod_only
def add_department(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()

        if not name:
            messages.error(request, "Department name is required.")
            return redirect("hod_add_department")

        Department.objects.create(name=name, code=code or None)
        messages.success(request, f"Department '{name}' created.")
        return redirect("hod_manage_departments")

    return render(request, "attendance/hod_add_department.html")


@hod_only
def edit_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        dept.name = request.POST.get("name", "").strip()
        dept.code = request.POST.get("code", "").strip() or None

        if not dept.name:
            messages.error(request, "Department name is required.")
            return redirect("hod_edit_department", pk=pk)

        dept.save()
        messages.success(request, f"Department '{dept.name}' updated.")
        return redirect("hod_manage_departments")

    return render(request, "attendance/hod_edit_department.html", {"department": dept})


@hod_only
def delete_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    name = dept.name
    dept.delete()
    messages.success(request, f"Department '{name}' deleted.")
    return redirect("hod_manage_departments")

# =====================================================
# ANALYTICS WRAPPERS (USE analytics.py ENGINE)
# =====================================================

@hod_only
def analytics_weekly(request):
    start_dt, end_dt, _ = aura_analytics.get_date_range_from_request(request)
    data = aura_analytics.weekly_class_overview(start_dt, end_dt)
    return JsonResponse(data)


@hod_only
def analytics_monthly(request):
    start_dt, end_dt, _ = aura_analytics.get_date_range_from_request(request)
    data = aura_analytics.monthly_trend(start_dt, end_dt)
    return JsonResponse(data)


@hod_only
def analytics_classwise(request):
    start_dt, end_dt, _ = aura_analytics.get_date_range_from_request(request)
    data = aura_analytics.classwise_distribution(start_dt, end_dt)
    return JsonResponse(data)


@hod_only
def analytics_subject_heatmap(request):
    start_dt, end_dt, _ = aura_analytics.get_date_range_from_request(request)
    data = aura_analytics.subject_heatmap_data(start_dt, end_dt)
    return JsonResponse(data)


@hod_only
def analytics_teacher_activity(request):
    start_dt, end_dt, _ = aura_analytics.get_date_range_from_request(request)
    data = aura_analytics.teacher_activity_data(start_dt, end_dt)
    return JsonResponse(data)


@hod_only
def analytics_absence_distribution(request):
    start_dt, end_dt, _ = aura_analytics.get_date_range_from_request(request)
    data = aura_analytics.absence_distribution_data(start_dt, end_dt)
    return JsonResponse(data)


# =====================================================
# ANALYTICS PAGE
# =====================================================

@hod_only
def hod_analytics_page(request):
    return render(request, "attendance/hod_analytics.html")

# =====================================================
# HOD PDF REPORTS
# 1) Student summary
# 2) Class summary
# 3) Teacher performance
# 4) Overall HOD overview (last 30 days)
# =====================================================

@hod_only
def hod_student_report_pdf(request, student_id):
    """
    Per-student summary: total present/absent, overall percentage,
    plus daily breakdown for the last 30 days.
    """
    start_30, end_30 = _last_30_days()

    student = get_object_or_404(Student, student_id=student_id)

    # All-time attendance
    qs_all = Attendance.objects.filter(student=student).select_related(
        "session", "session__class_group", "session__subject"
    )

    total_present = qs_all.filter(present=True).count()
    total_absent = qs_all.filter(present=False).count()
    total = total_present + total_absent
    percentage = round((total_present / total) * 100, 2) if total else 0

    # Last-30-days breakdown for table
    qs_30 = qs_all.filter(session__start_time__date__range=[start_30, end_30])

    attendances = []
    for att in qs_30.order_by("timestamp"):
        attendances.append({
            "date": att.timestamp.date(),
            "present": "Yes" if att.present else "No",
            "verified_by_face": "Yes" if att.verified_by_face else "No",
            "timestamp": att.timestamp.strftime("%Y-%m-%d %H:%M"),
        })

    context = {
        "student": student,
        "class_group": student.class_group,
        "department": student.class_group.department if student.class_group else None,
        "report_date": now(),

        "total_present": total_present,
        "total_absent": total_absent,
        "percentage": percentage,

        "attendances": attendances,
    }

    html_string = render_to_string(
        "attendance/hod_report_student.html",
        context,
        request=request,   # ensures {% static %} and {{ request }} work
    )
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="student_{student.student_id}_report.pdf"'
    return response


@hod_only
def hod_class_report_pdf(request, class_id):
    """
    Class summary: each student's present/absent/percentage
    (all-time + last 30 days).
    """
    start_30, end_30 = _last_30_days()
    class_group = get_object_or_404(ClassGroup, pk=class_id)

    students = Student.objects.filter(class_group=class_group).order_by("student_id")
    rows = []

    for s in students:
        qs = Attendance.objects.filter(student=s)

        total_present = qs.filter(present=True).count()
        total_absent = qs.filter(present=False).count()
        total = total_present + total_absent
        perc = round((total_present / total) * 100, 2) if total else 0

        qs30 = qs.filter(session__start_time__date__range=[start_30, end_30])
        p30 = qs30.filter(present=True).count()
        a30 = qs30.filter(present=False).count()
        t30 = p30 + a30
        perc30 = round((p30 / t30) * 100, 2) if t30 else 0

        rows.append({
            "student": s,
            "present": total_present,
            "absent": total_absent,
            "percentage": perc,
            "present_30": p30,
            "absent_30": a30,
            "percentage_30": perc30,
        })

    all_att = Attendance.objects.filter(session__class_group=class_group)
    class_present = all_att.filter(present=True).count()
    class_total = all_att.count()
    class_percentage = round((class_present / class_total) * 100, 2) if class_total else 0

    context = {
        "class_group": class_group,
        "department": class_group.department,
        "report_date": now(),
        "rows": rows,
        "class_total": class_total,
        "class_percentage": class_percentage,
    }

    html_string = render_to_string(
        "attendance/hod_report_class.html",
        context,
        request=request,
    )
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="class_{class_group.name}_report.pdf"'
    return response


@hod_only
def hod_teacher_report_pdf(request, teacher_id):
    """
    Teacher performance: sessions in last 7/30/90 days +
    average attendance in their sessions and bunk percentage.
    """
    teacher_user = get_object_or_404(User, pk=teacher_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=teacher_user)

    today = now().date()
    start_7 = today - timedelta(days=7)
    start_30 = today - timedelta(days=30)
    start_90 = today - timedelta(days=90)

    def session_count_between(start_date):
        return Session.objects.filter(
            teacher=teacher_user,
            start_time__date__range=[start_date, today],
        ).count()

    sessions_7 = session_count_between(start_7)
    sessions_30 = session_count_between(start_30)
    sessions_90 = session_count_between(start_90)

    teacher_sessions = Session.objects.filter(teacher=teacher_user)
    att_qs = Attendance.objects.filter(session__in=teacher_sessions)

    present = att_qs.filter(present=True).count()
    total = att_qs.count()
    avg_attendance = round((present / total) * 100, 2) if total else 0
    bunk_percentage = round(((total - present) / total) * 100, 2) if total else 0

    context = {
        "teacher": teacher_user,
        "profile": teacher_profile,
        "subjects": teacher_profile.subjects.all(),
        "classes": teacher_profile.classes.all(),
        "report_date": now(),
        "sessions_7": sessions_7,
        "sessions_30": sessions_30,
        "sessions_90": sessions_90,
        "avg_attendance": avg_attendance,
        "bunk_percentage": bunk_percentage,
    }

    html_string = render_to_string(
        "attendance/hod_report_teacher.html",
        context,
        request=request,
    )
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="teacher_{teacher_user.username}_report.pdf"'
    return response


@hod_only
def hod_overview_report_pdf(request):
    """
    Overall HOD dashboard-style summary for last 30 days.
    """
    start_30, end_30 = _last_30_days()

    sessions = Session.objects.filter(start_time__date__range=[start_30, end_30])
    attendance = Attendance.objects.filter(session__in=sessions)

    present = attendance.filter(present=True).count()
    total = attendance.count()
    avg_attendance = round((present / total) * 100, 2) if total else 0

    class_rows = []
    for cls in ClassGroup.objects.all().order_by("name"):
        cls_sessions = sessions.filter(class_group=cls)
        cls_att = attendance.filter(session__class_group=cls)

        p = cls_att.filter(present=True).count()
        t = cls_att.count()
        perc = round((p / t) * 100, 2) if t else 0

        class_rows.append({
            "class": cls,
            "sessions": cls_sessions.count(),
            "percentage": perc,
        })

    teacher_rows = []
    for tp in TeacherProfile.objects.select_related("user").all():
        t_sessions = sessions.filter(teacher=tp.user).count()
        teacher_rows.append({
            "teacher": tp.user,
            "sessions": t_sessions,
        })

    context = {
        "report_date": now(),
        "start_30": start_30,
        "end_30": end_30,
        "total_sessions": sessions.count(),
        "total_attendance_rows": total,
        "avg_attendance": avg_attendance,
        "class_rows": class_rows,
        "teacher_rows": teacher_rows,
    }

    html_string = render_to_string(
        "attendance/hod_report_overview.html",
        context,
        request=request,
    )
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="hod_overview_last30_report.pdf"'
    return response
