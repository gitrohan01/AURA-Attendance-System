from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    StudentViewSet,
    mark_attendance,
    start_session,
    end_session,
    device_heartbeat
)

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")

urlpatterns = [
    path("", include(router.urls)),
    path("attendance/", mark_attendance, name="mark_attendance"),
    path("start_session/", start_session, name="start_session"),
    path("end_session/", end_session, name="end_session"),
    path("heartbeat/", device_heartbeat, name="device_heartbeat"),
]
