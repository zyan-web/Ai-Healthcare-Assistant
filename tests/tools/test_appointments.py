from datetime import date, timedelta

from app.schemas.common import AppointmentStatus, ToolErrorCode
from app.schemas.tools import (
    AppointmentCancelArgs,
    AppointmentCreateArgs,
    AppointmentRescheduleArgs,
    AppointmentSearchArgs,
    AvailabilitySearchArgs,
)
from app.tools.appointments import (
    appointment_cancel,
    appointment_create,
    appointment_reschedule,
    appointment_search,
)
from app.tools.calendar import availability_search


def _next_monday() -> date:
    today = date.today()
    days_ahead = (0 - today.weekday()) % 7
    days_ahead = days_ahead or 7
    return today + timedelta(days=days_ahead)


def _any_patient_and_doctor(s):
    return next(iter(s.patients)), next(iter(s.doctors))


def test_appointment_create_then_search_finds_it(s):
    patient_id, doctor_id = _any_patient_and_doctor(s)
    target_date = _next_monday()
    slots = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots
    slot = slots[0]

    create_resp = appointment_create(
        AppointmentCreateArgs(
            patient_id=patient_id, doctor_id=doctor_id, target_date=target_date, start_time=slot
        ),
        s=s,
    )

    assert create_resp.success
    appt = create_resp.data.appointment
    assert appt.status == AppointmentStatus.CONFIRMED

    search_resp = appointment_search(AppointmentSearchArgs(patient_id=patient_id), s=s)
    assert any(a.appointment_id == appt.appointment_id for a in search_resp.data.appointments)


def test_appointment_create_conflict_on_double_booking(s):
    patient_id, doctor_id = _any_patient_and_doctor(s)
    other_patient_id = [p for p in s.patients if p != patient_id][0]
    target_date = _next_monday()
    slot = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots[0]

    first = appointment_create(
        AppointmentCreateArgs(
            patient_id=patient_id, doctor_id=doctor_id, target_date=target_date, start_time=slot
        ),
        s=s,
    )
    assert first.success

    second = appointment_create(
        AppointmentCreateArgs(
            patient_id=other_patient_id, doctor_id=doctor_id, target_date=target_date,
            start_time=slot,
        ),
        s=s,
    )

    assert not second.success
    assert second.error.code == ToolErrorCode.CONFLICT


def test_appointment_create_unknown_patient(s):
    doctor_id = next(iter(s.doctors))
    target_date = _next_monday()
    slot = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots[0]

    resp = appointment_create(
        AppointmentCreateArgs(
            patient_id="P9999", doctor_id=doctor_id, target_date=target_date, start_time=slot
        ),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND


def test_appointment_cancel_then_cannot_cancel_twice(s):
    patient_id, doctor_id = _any_patient_and_doctor(s)
    target_date = _next_monday()
    slot = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots[0]
    appt = appointment_create(
        AppointmentCreateArgs(
            patient_id=patient_id, doctor_id=doctor_id, target_date=target_date, start_time=slot
        ),
        s=s,
    ).data.appointment

    cancel_resp = appointment_cancel(
        AppointmentCancelArgs(appointment_id=appt.appointment_id, cancelled_by=patient_id), s=s
    )
    assert cancel_resp.success
    assert cancel_resp.data.appointment.status == AppointmentStatus.CANCELLED

    second_cancel = appointment_cancel(
        AppointmentCancelArgs(appointment_id=appt.appointment_id, cancelled_by=patient_id), s=s
    )
    assert not second_cancel.success
    assert second_cancel.error.code == ToolErrorCode.CONFLICT


def test_appointment_cancel_unknown_appointment(s):
    resp = appointment_cancel(
        AppointmentCancelArgs(appointment_id="A9999", cancelled_by="P0001"), s=s
    )
    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND


def test_appointment_reschedule_moves_slot_and_frees_old_one(s):
    patient_id, doctor_id = _any_patient_and_doctor(s)
    target_date = _next_monday()
    slots = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots
    original_slot, new_slot = slots[0], slots[1]

    appt = appointment_create(
        AppointmentCreateArgs(
            patient_id=patient_id, doctor_id=doctor_id, target_date=target_date,
            start_time=original_slot,
        ),
        s=s,
    ).data.appointment

    resp = appointment_reschedule(
        AppointmentRescheduleArgs(
            appointment_id=appt.appointment_id, new_date=target_date, new_start_time=new_slot,
            rescheduled_by=patient_id,
        ),
        s=s,
    )

    assert resp.success
    assert resp.data.appointment.start_time == new_slot
    assert resp.data.previous_start_time == original_slot

    # The old slot should be bookable again.
    refreshed_slots = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots
    assert original_slot in refreshed_slots
    assert new_slot not in refreshed_slots


def test_appointment_reschedule_conflict_with_existing_appointment(s):
    patient_id, doctor_id = _any_patient_and_doctor(s)
    other_patient_id = [p for p in s.patients if p != patient_id][0]
    target_date = _next_monday()
    slots = availability_search(
        AvailabilitySearchArgs(doctor_id=doctor_id, target_date=target_date), s=s
    ).data.available_slots
    slot_a, slot_b = slots[0], slots[1]

    appt_a = appointment_create(
        AppointmentCreateArgs(
            patient_id=patient_id, doctor_id=doctor_id, target_date=target_date, start_time=slot_a
        ),
        s=s,
    ).data.appointment
    appointment_create(
        AppointmentCreateArgs(
            patient_id=other_patient_id, doctor_id=doctor_id, target_date=target_date,
            start_time=slot_b,
        ),
        s=s,
    )

    resp = appointment_reschedule(
        AppointmentRescheduleArgs(
            appointment_id=appt_a.appointment_id, new_date=target_date, new_start_time=slot_b,
            rescheduled_by=patient_id,
        ),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.CONFLICT
