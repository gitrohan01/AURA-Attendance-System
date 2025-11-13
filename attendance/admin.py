from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *
from .models import FineRule, Device
from django.contrib.auth.admin import UserAdmin
from .models import User

admin.site.register(Student)
admin.site.register(TeacherProfile)
admin.site.register(Subject)
admin.site.register(ClassGroup)
admin.site.register(Session)
admin.site.register(Attendance)
admin.site.register(Holiday)



admin.site.register(FineRule)
admin.site.register(Device)


admin.site.register(User, UserAdmin)