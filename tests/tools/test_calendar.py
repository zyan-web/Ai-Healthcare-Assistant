from datetime import date, timedelta

from app.schemas.common import ToolErrorCode
from app.schemas.tools import AvailabilitySearchArgs, DoctorScheduleArgs, DoctorSearchArgs
from app.tools.calendar import doctor_schedule, doctor_search, availability_search


def _next_monday() -> date:
    today = date.today()
    days_ahead = (0 - today.weekday()) % 7
    days_ahead = days_ahead or 7
    return today + timedelta(days=days_ahead)


def test_doctor_search_by_specialty(s):
    any_doctor = next(iter(s.doctors.values()))

    resp = doctor_search(DoctorSearchArgs(query=any_doctor.specialty), s=s)

    assert resp.success
    assert any(d.doctor_id == any_doctor.doctor_id for d in resp.data.matches)


def test_doctor_search_empty_query_is_validation_error(s):
    resp = doctor_search(DoctorSearchArgs(query=""), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR


def test_doctor_schedule_working_day(s):
    doctor_id = next(iter(s.doctors))
    monday = _next_monday()

    resp = doctor_schedule(DoctorScheduleArgs(doctor_id=doctor_id, target_date=monday), s=s)

    assert resp.success
    assert resp.data.is_working_day is True


def test_doctor_schedule_unknown_doctor(s):
    resp = doctor_schedule(DoctorScheduleArgs(doctor_id="D9999", target_date=date.today()), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND


def test_availability_search_excludes_lunch_and_booked_slots(s):
    doctor_id = next(iter(s.doctors))
    monday = _next_monday()

    resp = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=monday, time_range="all_day"),
        s=s,
    )

    assert resp.success
    from datetime import time

    assert all(not (time(12, 0) <= slot < time(13, 0)) for slot in resp.data.available_slots)


def test_availability_search_morning_window(s):
    doctor_id = next(iter(s.doctors))
    monday = _next_monday()

    resp = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=monday, time_range="morning"),
        s=s,
    )

    assert resp.success
    from datetime import time

    assert all(slot < time(12, 0) for slot in resp.data.available_slots)


def test_availability_search_invalid_time_range(s):
    doctor_id = next(iter(s.doctors))

    resp = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=date.today(), time_range="night"),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
