"""Doctor / scheduling tools: doctor_search, doctor_schedule, availability_search."""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, time, timedelta

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.entities import DoctorSchedule
from app.schemas.tools import (
    AvailabilitySearchArgs,
    AvailabilitySearchData,
    DoctorScheduleArgs,
    DoctorScheduleData,
    DoctorSearchArgs,
    DoctorSearchData,
)

# Standard lunch break excluded from bookable slots (working_hours_policy).
LUNCH_START = time(12, 0)
LUNCH_END = time(13, 0)

TIME_RANGE_WINDOWS = {
    "morning": (time(0, 0), time(12, 0)),
    "afternoon": (time(12, 0), time(17, 0)),
    "evening": (time(17, 0), time(23, 59)),
    "all_day": (time(0, 0), time(23, 59)),
}


def doctor_search(args: DoctorSearchArgs, s: InMemoryStore = store) -> ToolResponse[DoctorSearchData]:
    q = args.query.strip().lower()
    if not q:
        return ToolResponse.fail(ToolErrorCode.VALIDATION_ERROR, "query must not be empty")

    matches = [
        d
        for d in s.doctors.values()
        if q in d.doctor_id.lower()
        or q in d.full_name.lower()
        or q in d.specialty.lower()
        or q in d.department.lower()
    ]
    return ToolResponse.ok(DoctorSearchData(matches=matches))


def doctor_schedule(
    args: DoctorScheduleArgs, s: InMemoryStore = store
) -> ToolResponse[DoctorScheduleData]:
    if args.doctor_id not in s.doctors:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No doctor found with id {args.doctor_id}"
        )
    schedule = s.schedules.get(args.doctor_id)
    if not schedule:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No schedule on file for doctor {args.doctor_id}"
        )
    is_working_day = any(
        wh.day_of_week == args.target_date.weekday() for wh in schedule.working_hours
    )
    return ToolResponse.ok(
        DoctorScheduleData(
            doctor_id=args.doctor_id,
            target_date=args.target_date,
            schedule=schedule,
            is_working_day=is_working_day,
        )
    )


def _generate_day_slots(schedule: DoctorSchedule, target_date: date_cls) -> list[time]:
    working_hours = [wh for wh in schedule.working_hours if wh.day_of_week == target_date.weekday()]
    slots: list[time] = []
    for wh in working_hours:
        cursor = datetime.combine(target_date, wh.start_time)
        end = datetime.combine(target_date, wh.end_time)
        step = timedelta(minutes=schedule.slot_minutes)
        while cursor + step <= end:
            slot_time = cursor.time()
            if not (LUNCH_START <= slot_time < LUNCH_END):
                slots.append(slot_time)
            cursor += step
    return slots


def availability_search(
    args: AvailabilitySearchArgs, s: InMemoryStore = store
) -> ToolResponse[AvailabilitySearchData]:
    if args.doctor_id not in s.doctors:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No doctor found with id {args.doctor_id}"
        )
    schedule = s.schedules.get(args.doctor_id)
    if not schedule:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No schedule on file for doctor {args.doctor_id}"
        )
    if args.time_range not in TIME_RANGE_WINDOWS:
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR,
            f"Unsupported time_range '{args.time_range}'. Use one of "
            f"{list(TIME_RANGE_WINDOWS)}.",
        )

    window_start, window_end = TIME_RANGE_WINDOWS[args.time_range]
    all_slots = _generate_day_slots(schedule, args.target_date)

    booked_times = {
        a.start_time for a in s.appointments_for_doctor_on_date(args.doctor_id, args.target_date)
    }

    available = [
        slot
        for slot in all_slots
        if window_start <= slot < window_end and slot not in booked_times
    ]
    return ToolResponse.ok(
        AvailabilitySearchData(
            doctor_id=args.doctor_id, target_date=args.target_date, available_slots=available
        )
    )
