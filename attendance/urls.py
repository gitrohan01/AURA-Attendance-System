from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from . import views

# --- Public pages ---
def index(request): 
    return render(request, 'attendance/index.html')

def about(request): 
    return render(request, 'attendance/about.html')

def hardware(request): 
    return render(request, 'attendance/hardware.html')

def contact(request): 
    return render(request, 'attendance/contact.html')


# --- Teacher Login ---
def teacher_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and hasattr(user, 'teacher_profile'):
            login(request, user)
            return redirect('teacher_dashboard')
        else:
            return render(request, 'attendance/teacher_login.html', {
                'error': 'Invalid credentials or user is not a Teacher'
            })
    return render(request, 'attendance/teacher_login.html')


# --- HOD Login ---
def hod_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and getattr(user, 'is_hod', False):
            login(request, user)
            return redirect('hod_dashboard')
        else:
            return render(request, 'attendance/hod_login.html', {
                'error': 'Invalid credentials or user is not an HOD'
            })
    return render(request, 'attendance/hod_login.html')


urlpatterns = [
    # --- Public routes ---
    path('', index, name='index'),
    path('about/', about, name='about'),
    path('hardware/', hardware, name='hardware'),
    path('contact/', contact, name='contact'),

    # --- Auth routes ---
    path('teacher/login/', teacher_login, name='teacher_login'),
    path('hod/login/', hod_login, name='hod_login'),

    # --- Teacher routes ---
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/class/<int:class_id>/', views.teacher_class_detail, name='teacher_class_detail'),

    # --- HOD routes ---
    path('hod/dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('hod/teacher/<int:teacher_id>/', views.hod_teacher_detail, name='hod_teacher_detail'),
]
