from attendance.models import *
from django.utils import timezone
import random
from datetime import datetime, timedelta

# ====================================
# SETTINGS
# ====================================
CLASS_NAME = "Sigma"
STUDENTS = list(Student.objects.filter(class_group__name=CLASS_NAME))
SUBJECTS = list(Subject.objects.all())
TEACHER_PROFILES = list(TeacherProfile.objects.all())

START_DATE = timezone.now() - timedelta(days=60)
END_DATE = timezone.now()

# Approx sessions per day
SESSIONS_PER_DAY = (5, 6)  # random between 5 and 6

# ====================================
# HELPERS
# ====================================

def get_teacher_for_subject(subject):
    """Return a teacher who teaches this subject."""
    for t in TEACHER_PROFILES:
        if subject in t.subjects.all():
            return t.user
    return None


def random_time(base_date, start_hour):
    """Return random time on that date with start hour."""
    hour = start_hour
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base_date.replace(hour=hour, minute=minute, second=second)


# ====================================
# GENERATION START
# ====================================

current_day = START_DATE

while current_day.date() <= END_DATE.date():

    # Skip Sundays
    if current_day.weekday() == 6:
        current_day += timedelta(days=1)
        continue

    # Number of sessions this day
    sessions_today = random.randint(*SESSIONS_PER_DAY)

    # Spread sessions hourly between 9 AM to 5 PM
    possible_slots = list(range(9, 17))  # 9am to 4pm start times
    random.shuffle(possible_slots)
    chosen_slots = possible_slots[:sessions_today]

    for slot in chosen_slots:

        # Pick random subject + teacher
        subject = random.choice(SUBJECTS)
        teacher = get_teacher_for_subject(subject)

        if teacher is None:
            continue  # skip if no teacher teaches this subject

        session_start = random_time(current_day, slot)
        session_end = session_start + timedelta(minutes=random.randint(45, 60))

        session_id = f"S_{subject.code}_{session_start.strftime('%Y%m%d_%H%M%S')}"

        session = Session.objects.create(
            session_id=session_id,
            subject=subject,
            class_group=ClassGroup.objects.get(name=CLASS_NAME),
            teacher=teacher,
            start_time=session_start,
            end_time=session_end,
        )

        # Attendance: randomly 2–6 absent
        absent_count = random.randint(2, 6)
        absent_students = random.sample(STUDENTS, absent_count)

        for stu in STUDENTS:
            present = stu not in absent_students

            Attendance.objects.create(
                session=session,
                student=stu,
                timestamp=session_start + timedelta(minutes=random.randint(0, 15)),
                verified_by_face=True,  # always TRUE now
                present=present,
                source="RFID",
            )

    current_day += timedelta(days=1)

print("✔ DONE — full fake dataset generated successfully!")
print("✔ Sessions:", Session.objects.count())
print("✔ Attendance:", Attendance.objects.count())
