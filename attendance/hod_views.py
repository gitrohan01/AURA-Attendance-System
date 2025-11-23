# attendance/hod_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
import csv
import io
from django.http import JsonResponse
from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta
from .models import Attendance, Session, ClassGroup, Subject, TeacherProfile

from .models import (
    User, Student, ClassGroup, Subject, TeacherProfile, Department
)


def is_hod(user):
    return user.is_authenticated and getattr(user, "is_hod", False)


def hod_only(view_func):
    return login_required(user_passes_test(is_hod)(view_func))


# =========================
# STUDENTS CRUD
# =========================

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
        student_id = request.POST.get("student_id").strip()
        first_name = request.POST.get("first_name").strip()
        last_name = request.POST.get("last_name").strip()
        email = request.POST.get("email").strip()
        nfc_uid = request.POST.get("nfc_uid").strip()
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

    return render(request, "attendance/hod_add_student.html", {
        "classes": classes,
    })


@hod_only
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    classes = ClassGroup.objects.all().order_by("name")

    if request.method == "POST":
        student.student_id = request.POST.get("student_id").strip()
        student.first_name = request.POST.get("first_name").strip()
        student.last_name = request.POST.get("last_name").strip()
        student.email = request.POST.get("email").strip() or None
        student.nfc_uid = request.POST.get("nfc_uid").strip() or None
        student.class_group_id = request.POST.get("class_group") or None

        if not student.student_id or not student.first_name:
            messages.error(request, "Student ID and First Name are required.")
            return redirect("hod_edit_student", pk=student.pk)

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


# =========================
# TEACHERS CRUD
# =========================

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
        nfc_uid = request.POST.get("nfc_uid", "").strip()
        class_ids = request.POST.getlist("classes")
        subject_ids = request.POST.getlist("subjects")

        profile.nfc_uid = nfc_uid or None
        profile.save()
        profile.classes.set(class_ids)
        profile.subjects.set(subject_ids)

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
    uname = profile.user.username
    profile.delete()
    messages.success(request, f"Teacher profile for {uname} deleted.")
    return redirect("hod_manage_teachers")


# =========================
# CLASSGROUP CRUD
# =========================

@hod_only
def manage_classes(request):
    classes = ClassGroup.objects.select_related("department").order_by("name")
    return render(request, "attendance/hod_manage_classes.html", {
        "classes": classes,
    })


@hod_only
def add_class(request):
    from .models import Department
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        name = request.POST.get("name").strip()
        description = request.POST.get("description").strip()
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
    from .models import Department
    c = get_object_or_404(ClassGroup, pk=pk)
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        c.name = request.POST.get("name").strip()
        c.description = request.POST.get("description").strip()
        c.department_id = request.POST.get("department") or None

        if not c.name:
            messages.error(request, "Class name is required.")
            return redirect("hod_edit_class", pk=c.pk)

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


# =========================
# SUBJECT CRUD
# =========================

@hod_only
def manage_subjects(request):
    subjects = Subject.objects.select_related("department").order_by("code")
    return render(request, "attendance/hod_manage_subjects.html", {
        "subjects": subjects,
    })


@hod_only
def add_subject(request):
    from .models import Department
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        code = request.POST.get("code").strip()
        name = request.POST.get("name").strip()
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
    from .models import Department
    subject = get_object_or_404(Subject, pk=pk)
    departments = Department.objects.all().order_by("name")

    if request.method == "POST__":
        subject.code = request.POST.get("code").strip()
        subject.name = request.POST.get("name").strip()
        subject.department_id = request.POST.get("department") or None

        if not subject.code or not subject.name:
            messages.error(request, "Subject code and name are required.")
            return redirect("hod_edit_subject", pk=subject.pk)

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
    code = subject.code
    subject.delete()
    messages.success(request, f"Subject {code} deleted.")
    return redirect("hod_manage_subjects")


# =========================
# BULK STUDENT CSV IMPORT
# =========================

@hod_only
def import_students(request):
    """
    CSV columns:
    student_id,first_name,last_name,email,nfc_uid,class_group_name
    """
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
                defaults=defaults
            )
            created += is_created
            updated += (not is_created)

        messages.success(request, f"Import complete: Created {created}, Updated {updated}")
        return redirect("hod_manage_students")

    return render(request, "attendance/hod_import_students.html", {
        "classes": classes,
    })


# =========================
# DEPARTMENTS CRUD
# =========================

@hod_only
def manage_departments(request):
    departments = Department.objects.all().order_by("name")
    return render(request, "attendance/hod_manage_departments.html", {
        "departments": departments,
    })


@hod_only
def add_department(request):

    if request.method == "POST":
        name = request.POST.get("name").strip()
        code = request.POST.get("code").strip()

        if not name:
            messages.error(request, "Department name is required.")
            return redirect("hod_add_department")

        Department.objects.create(
            name=name,
            code=code or None
        )

        messages.success(request, f"Department '{name}' created.")
        return redirect("hod_manage_departments")

    return render(request, "attendance/hod_add_department.html")


@hod_only
def edit_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        dept.name = request.POST.get("name").strip()
        dept.code = request.POST.get("code").strip() or None

        if not dept.name:
            messages.error(request, "Department name is required.")
            return redirect("hod_edit_department", pk=dept.pk)

        dept.save()
        messages.success(request, f"Department '{dept.name}' updated.")
        return redirect("hod_manage_departments")

    return render(request, "attendance/hod_edit_department.html", {
        "department": dept
    })


@hod_only
def delete_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    name = dept.name
    dept.delete()
    messages.success(request, f"Department '{name}' deleted.")
    return redirect("hod_manage_departments")


@hod_only
def analytics_weekly(request):
    last_7 = now() - timedelta(days=7)

    classes = ClassGroup.objects.all()
    labels, values = [], []

    for cls in classes:
        total_sessions = Session.objects.filter(
            class_group=cls, 
            start_time__gte=last_7
        ).count()

        total_present = Attendance.objects.filter(
            session__class_group=cls,
            session__start_time__gte=last_7,
            present=True
        ).count()

        percentage = round((total_present / total_sessions) * 100, 2) if total_sessions else 0

        labels.append(cls.name)
        values.append(percentage)

    return JsonResponse({"labels": labels, "values": values})


@hod_only
def analytics_monthly(request):
    last_30 = now() - timedelta(days=30)

    data = (
        Attendance.objects.filter(timestamp__gte=last_30)
        .extra({"day": "date(timestamp)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    labels = [str(x["day"]) for x in data]
    values = [x["count"] for x in data]

    return JsonResponse({"labels": labels, "values": values})


@hod_only
def analytics_classwise(request):
    classes = ClassGroup.objects.all()
    labels, values = [], []

    for cls in classes:
        total = Attendance.objects.filter(session__class_group=cls).count()
        labels.append(cls.name)
        values.append(total)

    return JsonResponse({"labels": labels, "values": values})


@hod_only
def analytics_subject_heatmap(request):
    subjects = Subject.objects.all()

    labels, present_list, absent_list = [], [], []

    for s in subjects:
        present = Attendance.objects.filter(session__subject=s, present=True).count()
        absent = Attendance.objects.filter(session__subject=s, present=False).count()

        labels.append(s.code)
        present_list.append(present)
        absent_list.append(absent)

    return JsonResponse({
        "labels": labels,
        "present": present_list,
        "absent": absent_list
    })

@hod_only
def analytics_teacher_activity(request):
    teachers = TeacherProfile.objects.select_related("user")

    labels, values = [], []

    for t in teachers:
        count = Session.objects.filter(teacher=t.user).count()
        labels.append(t.user.get_full_name() or t.user.username)
        values.append(count)

    return JsonResponse({"labels": labels, "values": values})


@hod_only
def analytics_absence_distribution(request):
    total_present = Attendance.objects.filter(present=True).count()
    total_absent = Attendance.objects.filter(present=False).count()

    return JsonResponse({
        "labels": ["Present", "Absent"],
        "values": [total_present, total_absent]
    })


@hod_only
def hod_analytics_page(request):
    return render(request, "attendance/hod_analytics.html")
