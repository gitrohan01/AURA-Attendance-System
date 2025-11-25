# attendance/analytics.py

from datetime import datetime, timedelta
from django.utils.timezone import now, localtime
from django.db.models import Count
from django.db.models.functions import TruncDate

from .models import Attendance, Session, ClassGroup, Subject, TeacherProfile


# ---------------------------------------------------------
# DATE RANGE PARSER
# ---------------------------------------------------------
def get_date_range_from_request(request):
    range_type = request.GET.get("range", "last30")

    today = localtime().date()   # IMPORTANT: use LOCAL DATE
    label = ""

    if range_type == "last7":
        start = today - timedelta(days=7)
        end = today
        label = "Last 7 days"

    elif range_type == "last30":
        start = today - timedelta(days=30)
        end = today
        label = "Last 30 days"

    elif range_type == "this_month":
        start = today.replace(day=1)
        end = today
        label = "This month"

    elif range_type == "custom":
        s = request.GET.get("start_date")
        e = request.GET.get("end_date")

        try:
            start = datetime.strptime(s, "%Y-%m-%d").date() if s else today - timedelta(days=30)
        except:
            start = today - timedelta(days=30)

        try:
            end = datetime.strptime(e, "%Y-%m-%d").date() if e else today
        except:
            end = today

        if end < start:
            start, end = end, start

        label = f"Custom {start} → {end}"

    else:
        start = today - timedelta(days=30)
        end = today
        label = "Last 30 days"

    return start, end, label


# ---------------------------------------------------------
# HELPER — correct UTC → local date truncation
# ---------------------------------------------------------
def truncate_local_date(field_name):
    """Ensures date grouping is done in LOCAL TIMEZONE, not UTC."""
    return TruncDate(field_name, tzinfo=localtime().tzinfo)


# ---------------------------------------------------------
# 1) Weekly Class Overview
# ---------------------------------------------------------
def weekly_class_overview(start_date, end_date):
    labels, values = [], []

    classes = ClassGroup.objects.all().order_by("name")

    for cls in classes:
        total_sessions = Session.objects.filter(
            class_group=cls,
            start_time__date__range=[start_date, end_date]
        ).count()

        total_present = Attendance.objects.filter(
            session__class_group=cls,
            session__start_time__date__range=[start_date, end_date],
            present=True
        ).count()

        percentage = round((total_present / total_sessions) * 100, 2) if total_sessions else 0

        labels.append(cls.name)
        values.append(percentage)

    return {"labels": labels, "values": values}


# ---------------------------------------------------------
# 2) Monthly Trend (DATE-WISE)
# ---------------------------------------------------------
def monthly_trend(start_date, end_date):
    qs = (
        Attendance.objects.filter(
            session__start_time__date__range=[start_date, end_date]
        )
        .annotate(day=truncate_local_date("session__start_time"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    labels = [str(x["day"]) for x in qs]
    values = [x["count"] for x in qs]

    return {"labels": labels, "values": values}


# ---------------------------------------------------------
# 3) Class-wise Attendance
# ---------------------------------------------------------
def classwise_distribution(start_date, end_date):
    labels, values = [], []

    for cls in ClassGroup.objects.all().order_by("name"):
        count = Attendance.objects.filter(
            session__class_group=cls,
            session__start_time__date__range=[start_date, end_date]
        ).count()

        labels.append(cls.name)
        values.append(count)

    return {"labels": labels, "values": values}


# ---------------------------------------------------------
# 4) Subject Heatmap
# ---------------------------------------------------------
def subject_heatmap_data(start_date, end_date):
    labels, present_list, absent_list = [], [], []

    for subj in Subject.objects.all().order_by("code"):
        present = Attendance.objects.filter(
            session__subject=subj,
            session__start_time__date__range=[start_date, end_date],
            present=True
        ).count()

        absent = Attendance.objects.filter(
            session__subject=subj,
            session__start_time__date__range=[start_date, end_date],
            present=False
        ).count()

        labels.append(subj.code)
        present_list.append(present)
        absent_list.append(absent)

    return {"labels": labels, "present": present_list, "absent": absent_list}


# ---------------------------------------------------------
# 5) Teacher Activity
# ---------------------------------------------------------
def teacher_activity_data(start_date, end_date):
    labels, values = [], []

    teachers = TeacherProfile.objects.select_related("user")

    for t in teachers:
        count = Session.objects.filter(
            teacher=t.user,
            start_time__date__range=[start_date, end_date]
        ).count()

        labels.append(t.user.get_full_name() or t.user.username)
        values.append(count)

    return {"labels": labels, "values": values}


# ---------------------------------------------------------
# 6) Overall Attendance Distribution
# ---------------------------------------------------------
def absence_distribution_data(start_date, end_date):
    present_count = Attendance.objects.filter(
        session__start_time__date__range=[start_date, end_date],
        present=True
    ).count()

    absent_count = Attendance.objects.filter(
        session__start_time__date__range=[start_date, end_date],
        present=False
    ).count()

    return {
        "labels": ["Present", "Absent"],
        "values": [present_count, absent_count],
    }
