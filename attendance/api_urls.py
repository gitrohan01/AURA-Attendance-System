from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    StudentViewSet,
    mark_attendance,
    start_session,
    end_session,
    device_heartbeat
)

from .api_views_iot import iot_session_upload

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")

urlpatterns = [
    path("", include(router.urls)),
    path("attendance/", mark_attendance, name="mark_attendance"),
    path("start_session/", start_session, name="start_session"),
    path("end_session/", end_session, name="end_session"),
    path("heartbeat/", device_heartbeat, name="device_heartbeat"),
]

urlpatterns += [
    path("iot/session/upload/", iot_session_upload),
]
