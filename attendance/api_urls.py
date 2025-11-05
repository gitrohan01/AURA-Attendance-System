from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import StudentViewSet, mark_attendance

router = DefaultRouter()
router.register('students', StudentViewSet, basename='student')

urlpatterns = [
    path('', include(router.urls)),
    path('attendance/', mark_attendance, name='mark_attendance'),
]
