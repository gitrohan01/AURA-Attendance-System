from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User, Student, TeacherProfile, Subject, ClassGroup,
    Session, Attendance, Holiday, FineRule, Device,
    PendingSession, PendingStudent, Department
)

# ------------------------------
# Custom User Admin
# ------------------------------
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "is_hod",
        "is_teacher",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "is_hod",
        "is_teacher",
        "is_staff",
        "is_active",
    )

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Roles", {"fields": ("is_hod", "is_teacher", "is_staff", "is_superuser", "is_active")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "password1",
                "password2",
                "is_hod",
                "is_teacher",
                "is_staff",
            ),
        }),
    )

# ------------------------------
# Register other models
# ------------------------------
admin.site.register(Student)
admin.site.register(TeacherProfile)
admin.site.register(Subject)
admin.site.register(ClassGroup)
admin.site.register(Session)
admin.site.register(Attendance)
admin.site.register(Holiday)
admin.site.register(FineRule)
admin.site.register(Device)
admin.site.register(Department)
admin.site.register(PendingSession)
admin.site.register(PendingStudent)
