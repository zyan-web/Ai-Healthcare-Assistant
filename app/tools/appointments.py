"""Appointment action + lookup tools.

appointment_create and appointment_reschedule both re-check the target
slot against the live store immediately before writing (project docs,
section 7: "Critical rule: availability can change between the first
search and the final write... If the slot is taken, it must not report
success; it should offer alternatives."). That check lives here, in
deterministic code, rather than trusting the LLM's earlier availability
search — this is what makes the guarantee hold even in a race.
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, time, timedelta

from app.data.store import InMemoryStore, store
from app.schemas.common import AppointmentStatus, ToolErrorCode, ToolResponse
from app.schemas.entities import Appointment, AppointmentEvent
from app.schemas.tools import (
    AppointmentCancelArgs,
    AppointmentCancelData,
    AppointmentCreateArgs,
    AppointmentCreateData,
    AppointmentRescheduleArgs,
    AppointmentRescheduleData,
    AppointmentSearchArgs,
    AppointmentSearchData,
)


def _slot_conflict(
    s: InMemoryStore,
    doctor_id: str,
    target_date: date_cls,
    start_time: time,
    exclude_appointment_id: str | None = None,
) -> bool:
    for appt in s.appointments_for_doctor_on_date(doctor_id, target_date):
        if appt.appointment_id == exclude_appointment_id:
            continue
        if appt.start_time == start_time:
            return True
    return False


def appointment_search(
    args: AppointmentSearchArgs, s: InMemoryStore = store
) -> ToolResponse[AppointmentSearchData]:
    results = list(s.appointments.values())

    if args.patient_id:
        results = [a for a in results if a.patient_id == args.patient_id]
    if args.doctor_id:
        results = [a for a in results if a.doctor_id == args.doctor_id]
    if args.date_from:
        results = [a for a in results if a.date >= args.date_from]
    if args.date_to:
        results = [a for a in results if a.date <= args.date_to]
    if args.status:
        results = [a for a in results if a.status == args.status]

    results.sort(key=lambda a: (a.date, a.start_time))
    return ToolResponse.ok(AppointmentSearchData(appointments=results))


def appointment_create(
    args: AppointmentCreateArgs, s: InMemoryStore = store
) -> ToolResponse[AppointmentCreateData]:
    if args.patient_id not in s.patients:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No patient found with id {args.patient_id}"
        )
    if args.doctor_id not in s.doctors:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No doctor found with id {args.doctor_id}"
        )
    schedule = s.schedules.get(args.doctor_id)
    if not schedule:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No schedule on file for doctor {args.doctor_id}"
        )

    if _slot_conflict(s, args.doctor_id, args.target_date, args.start_time):
        return ToolResponse.fail(
            ToolErrorCode.CONFLICT,
            f"{args.start_time.isoformat()} on {args.target_date.isoformat()} is no "
            f"longer available for doctor {args.doctor_id}.",
        )

    end_dt = datetime.combine(args.target_date, args.start_time) + timedelta(
        minutes=schedule.slot_minutes
    )
    appt_id = s.next_id("A")
    now = datetime.now()
    appointment = Appointment(
        appointment_id=appt_id,
        patient_id=args.patient_id,
        doctor_id=args.doctor_id,
        date=args.target_date,
        start_time=args.start_time,
        end_time=end_dt.time(),
        status=AppointmentStatus.CONFIRMED,
        created_at=now,
        updated_at=now,
        reason=args.reason,
    )
    s.appointments[appt_id] = appointment

    event_id = s.next_id("EVT")
    s.appointment_events[event_id] = AppointmentEvent(
        event_id=event_id,
        appointment_id=appt_id,
        event_type="CREATED",
        occurred_at=now,
        details={"doctor_id": args.doctor_id, "patient_id": args.patient_id},
    )

    return ToolResponse.ok(AppointmentCreateData(appointment=appointment))


def appointment_cancel(
    args: AppointmentCancelArgs, s: InMemoryStore = store
) -> ToolResponse[AppointmentCancelData]:
    appointment = s.appointments.get(args.appointment_id)
    if not appointment:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No appointment found with id {args.appointment_id}"
        )
    if appointment.status == AppointmentStatus.CANCELLED:
        return ToolResponse.fail(
            ToolErrorCode.CONFLICT, f"Appointment {args.appointment_id} is already cancelled."
        )

    now = datetime.now()
    updated = appointment.model_copy(
        update={"status": AppointmentStatus.CANCELLED, "updated_at": now}
    )
    s.appointments[args.appointment_id] = updated

    event_id = s.next_id("EVT")
    s.appointment_events[event_id] = AppointmentEvent(
        event_id=event_id,
        appointment_id=args.appointment_id,
        event_type="CANCELLED",
        occurred_at=now,
        details={"cancelled_by": args.cancelled_by, "reason": args.reason},
    )

    return ToolResponse.ok(AppointmentCancelData(appointment=updated))


def appointment_reschedule(
    args: AppointmentRescheduleArgs, s: InMemoryStore = store
) -> ToolResponse[AppointmentRescheduleData]:
    appointment = s.appointments.get(args.appointment_id)
    if not appointment:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No appointment found with id {args.appointment_id}"
        )
    if appointment.status == AppointmentStatus.CANCELLED:
        return ToolResponse.fail(
            ToolErrorCode.CONFLICT,
            f"Appointment {args.appointment_id} is cancelled and cannot be rescheduled.",
        )

    schedule = s.schedules.get(appointment.doctor_id)
    if not schedule:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No schedule on file for doctor {appointment.doctor_id}"
        )

    if _slot_conflict(
        s, appointment.doctor_id, args.new_date, args.new_start_time,
        exclude_appointment_id=appointment.appointment_id,
    ):
        return ToolResponse.fail(
            ToolErrorCode.CONFLICT,
            f"{args.new_start_time.isoformat()} on {args.new_date.isoformat()} is no "
            f"longer available for doctor {appointment.doctor_id}.",
        )

    previous_date = appointment.date
    previous_start_time = appointment.start_time

    end_dt = datetime.combine(args.new_date, args.new_start_time) + timedelta(
        minutes=schedule.slot_minutes
    )
    now = datetime.now()
    updated = appointment.model_copy(
        update={
            "date": args.new_date,
            "start_time": args.new_start_time,
            "end_time": end_dt.time(),
            "updated_at": now,
        }
    )
    s.appointments[appointment.appointment_id] = updated

    event_id = s.next_id("EVT")
    s.appointment_events[event_id] = AppointmentEvent(
        event_id=event_id,
        appointment_id=appointment.appointment_id,
        event_type="RESCHEDULED",
        occurred_at=now,
        details={
            "rescheduled_by": args.rescheduled_by,
            "previous_date": previous_date.isoformat(),
            "previous_start_time": previous_start_time.isoformat(),
        },
    )

    return ToolResponse.ok(
        AppointmentRescheduleData(
            appointment=updated,
            previous_date=previous_date,
            previous_start_time=previous_start_time,
        )
    )
