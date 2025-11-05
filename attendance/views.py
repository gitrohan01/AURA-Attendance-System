from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import *
from .utils import attendance_percentage
from datetime import date, timedelta

# --- Helper permission checks ---
def is_teacher(user):
    return user.is_authenticated and user.is_teacher

def is_hod(user):
    return user.is_authenticated and user.is_hod

# -------------------------------
@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    teacher = request.user
    teacher_profile = teacher.teacher_profile
    classes = teacher_profile.classes.all()
    subjects = teacher_profile.subjects.all()
    return render(request, 'attendance/teacher_dashboard.html', {
        'classes': classes,
        'subjects': subjects,
    })


@login_required
@user_passes_test(is_teacher)
def teacher_class_detail(request, class_id):
    class_group = get_object_or_404(ClassGroup, id=class_id)
    teacher = request.user
    sessions = Session.objects.filter(class_group=class_group, teacher=teacher).order_by('-start_time')

    # For demo: show current week's attendance summary
    start = date.today() - timedelta(days=7)
    end = date.today()
    students = Student.objects.filter(class_group=class_group)

    summary = []
    for stud in students:
        perc = attendance_percentage(stud, class_group, None, start, end)
        summary.append({
            'student': stud,
            'percentage': perc,
        })

    return render(request, 'attendance/teacher_class_detail.html', {
        'class_group': class_group,
        'sessions': sessions,
        'summary': summary,
    })


@login_required
@user_passes_test(is_hod)
def hod_dashboard(request):
    teachers = User.objects.filter(is_teacher=True)
    return render(request, 'attendance/hod_dashboard.html', {'teachers': teachers})


@login_required
@user_passes_test(is_hod)
def hod_teacher_detail(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id)
    sessions = Session.objects.filter(teacher=teacher)
    return render(request, 'attendance/hod_teacher_detail.html', {
        'teacher': teacher,
        'sessions': sessions,
    })
