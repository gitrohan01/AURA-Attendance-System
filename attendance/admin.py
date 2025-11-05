from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *

admin.site.register(Student)
admin.site.register(TeacherProfile)
admin.site.register(Subject)
admin.site.register(ClassGroup)
admin.site.register(Session)
admin.site.register(Attendance)
admin.site.register(Holiday)
