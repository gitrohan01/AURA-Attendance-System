from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# --- User model ------------------------------------------------------------
class User(AbstractUser):
    # Use Django's auth; extend if you want extra fields (phone, dept)
    is_teacher = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# --- Core school models ----------------------------------------------------
class Department(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassGroup(models.Model):
    """
    A class / batch (e.g. 'BCA-2025' or 'CS101-SectionA').
    """
    name = models.CharField(max_length=120, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    # optional timings, room etc
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True)  # stud_0001
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True, null=True)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.SET_NULL, null=True, blank=True)
    nfc_uid = models.CharField(max_length=100, blank=True, null=True)  # card UID
    metadata = models.JSONField(blank=True, null=True)  # any extra info

    def __str__(self):
        return f"{self.student_id} | {self.first_name} {self.last_name}"


# --- Teacher assignment ----------------------------------------------------
class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    # subjects they can teach (M2M)
    subjects = models.ManyToManyField(Subject, blank=True)
    classes = models.ManyToManyField(ClassGroup, blank=True)  # classes they're assigned to

    def __str__(self):
        return f"Teacher: {self.user.username}"


# --- Sessions and schedule -------------------------------------------------
class Session(models.Model):
    """
    A session corresponds to one class occurrence (one lecture).
    Teachers start a session (start_time) and later end it (end_time).
    session_key should be unique for daily grouping e.g. CS101-2025-11-05-1
    """
    session_id = models.CharField(max_length=80)  # logical ID e.g. 'S20251104_1' or server-generated
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # mark if a session was cancelled / holiday etc.
    cancelled = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['class_group', 'subject', 'start_time']),
        ]
    def __str__(self):
        return f"{self.session_id} | {self.subject} | {self.class_group}"


# --- Attendance (actual records) -------------------------------------------
class Attendance(models.Model):
    session = models.ForeignKey('Session', on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    verified_by_face = models.BooleanField(default=False)
    present = models.BooleanField(default=True)   # True = Present, False = Absent
    source = models.CharField(max_length=32, default='RFID+FACE')  # or 'Manual', 'RFID', 'Face'
    extra = models.JSONField(blank=True, null=True)  # optional metadata (e.g. camera score)

    class Meta:
        unique_together = ('session', 'student')
        ordering = ['-timestamp']

    def __str__(self):
        status = "Present" if self.present else "Absent"
        return f"{self.student.student_id} | {self.session.session_id} | {status}"

# --- Holidays / non-teaching days ------------------------------------------
class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    applies_to = models.ManyToManyField(ClassGroup, blank=True)  # if empty => applies to all

    def __str__(self):
        return f"{self.date} - {self.name}"


# --- Enrollment history / academic calendar --------------------------------
class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    joined_on = models.DateField(null=True, blank=True)
    left_on = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'class_group')


# --- Reports / exported logs optional model --------------------------------
class ExportLog(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    params = models.JSONField()   # filters used
    file_path = models.CharField(max_length=300)  # where CSV/XLSX is saved
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Export {self.id} by {self.created_by} at {self.created_at}"
