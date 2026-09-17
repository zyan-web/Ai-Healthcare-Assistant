"""
Synthetic data generation (step 2 of the dev order).

Deterministic (seeded) fake data so tools and tests are reproducible.
Never points at real patients, providers, or billing systems.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from faker import Faker

from app.core.config import settings
from app.data.store import InMemoryStore, store
from app.schemas.common import AppointmentStatus, Role
from app.schemas.entities import (
    Appointment,
    BillingRecord,
    Doctor,
    DoctorSchedule,
    InsuranceRecord,
    Patient,
    PolicyDocument,
    User,
    WorkingHours,
)

SPECIALTIES = [
    ("Cardiology", "Cardiology Dept."),
    ("Dermatology", "Dermatology Dept."),
    ("Pediatrics", "Pediatrics Dept."),
    ("Orthopedics", "Orthopedics Dept."),
    ("General Practice", "General Medicine Dept."),
]

INSURANCE_PROVIDERS = ["BlueShield Health", "MediCare Plus", "Horizon Care", "UnitedWell"]

POLICY_DOCS = [
    (
        "cancellation_policy",
        "Appointment Cancellation Policy",
        "cancellation",
        "Patients may cancel an appointment free of charge up to 24 hours before "
        "the scheduled start time. Cancellations made within 24 hours of the "
        "appointment are subject to a $25 late-cancellation fee, waived for "
        "first-time occurrences. No-shows without cancellation are billed the "
        "full late-cancellation fee.",
        ["cancellation", "fees", "no-show"],
    ),
    (
        "reschedule_policy",
        "Appointment Rescheduling Policy",
        "scheduling",
        "Appointments may be rescheduled without penalty if the request is made "
        "at least 4 hours before the original start time, subject to provider "
        "availability. Rescheduling within 4 hours is treated as a cancellation "
        "under the cancellation policy plus a new booking.",
        ["reschedule", "scheduling"],
    ),
    (
        "refund_policy",
        "Billing Refund Policy",
        "billing",
        "Overpayments are refunded to the original payment method within 10 "
        "business days of request. Refunds for cancelled appointments already "
        "billed follow the cancellation policy fee schedule.",
        ["refund", "billing"],
    ),
    (
        "communication_policy",
        "Patient Communication Policy",
        "communication",
        "Appointment confirmations and reminders may be sent by email or SMS "
        "according to patient preference. Reminders are sent 24 hours before "
        "the appointment. Bulk communications to more than 25 recipients "
        "require staff approval before sending.",
        ["communication", "reminders", "bulk"],
    ),
    (
        "escalation_policy",
        "Clinical and Sensitive Request Escalation Policy",
        "escalation",
        "Any request seeking medical diagnosis, treatment advice, or medication "
        "guidance is outside the scope of the administrative agent and must be "
        "escalated to a human clinician rather than answered directly. Requests "
        "involving suspected abuse, self-harm, or emergencies must be escalated "
        "immediately with high priority.",
        ["escalation", "clinical", "safety"],
    ),
    (
        "working_hours_policy",
        "Standard Provider Working Hours",
        "scheduling",
        "Standard provider working hours are Monday through Friday, 09:00 to "
        "17:00, in 30-minute appointment slots, excluding a 12:00-13:00 lunch "
        "break. Some providers may have reduced or extended hours as reflected "
        "in their individual schedule.",
        ["scheduling", "working-hours"],
    ),
]


def _seed_doctors(fake: Faker, s: InMemoryStore) -> list[Doctor]:
    doctors = []
    for specialty, department in SPECIALTIES:
        doctor_id = s.next_id("D")
        doctor = Doctor(
            doctor_id=doctor_id,
            full_name=f"Dr. {fake.last_name()}",
            specialty=specialty,
            department=department,
            email=fake.unique.email(),
        )
        s.doctors[doctor_id] = doctor
        doctors.append(doctor)

        # Standard Mon-Fri 09:00-17:00 schedule, per working_hours_policy.
        working_hours = [
            WorkingHours(day_of_week=d, start_time=time(9, 0), end_time=time(17, 0))
            for d in range(0, 5)
        ]
        s.schedules[doctor_id] = DoctorSchedule(
            doctor_id=doctor_id, working_hours=working_hours, slot_minutes=30
        )
    return doctors


def _seed_patients(fake: Faker, s: InMemoryStore, count: int = 12) -> list[Patient]:
    patients = []
    for _ in range(count):
        patient_id = s.next_id("P")
        user_id = patient_id
        full_name = fake.name()
        email = fake.unique.email()
        s.users[user_id] = User(
            user_id=user_id, role=Role.PATIENT, email=email, display_name=full_name
        )
        patient = Patient(
            patient_id=patient_id,
            user_id=user_id,
            full_name=full_name,
            date_of_birth=fake.date_of_birth(minimum_age=1, maximum_age=90),
            phone=fake.phone_number(),
            email=email,
            insurance_id=None,
        )
        s.patients[patient_id] = patient
        patients.append(patient)
    return patients


def _seed_staff(s: InMemoryStore) -> None:
    s.users["S001"] = User(
        user_id="S001", role=Role.RECEPTIONIST, email="reception@clinic.example",
        display_name="Reception Desk",
    )
    s.users["S002"] = User(
        user_id="S002", role=Role.BILLING, email="billing@clinic.example",
        display_name="Billing Office",
    )
    s.users["S003"] = User(
        user_id="S003", role=Role.ADMIN, email="admin@clinic.example",
        display_name="Clinic Admin",
    )


def _seed_insurance(fake: Faker, s: InMemoryStore, patients: list[Patient]) -> None:
    for i, patient in enumerate(patients):
        insurance_id = s.next_id("INS")
        status = "ACTIVE"
        if i % 5 == 0:
            status = "EXPIRED"
        elif i % 7 == 0:
            status = "INACTIVE"
        valid_until = date.today() + timedelta(days=180) if status == "ACTIVE" else date.today() - timedelta(days=30)
        s.insurance_records[insurance_id] = InsuranceRecord(
            insurance_id=insurance_id,
            patient_id=patient.patient_id,
            provider_name=random.choice(INSURANCE_PROVIDERS),
            policy_number=fake.bothify(text="POL-########"),
            status=status,
            valid_until=valid_until,
        )
        patient.insurance_id = insurance_id


def _seed_billing(fake: Faker, s: InMemoryStore, patients: list[Patient]) -> None:
    for patient in patients:
        if random.random() < 0.6:
            billing_id = s.next_id("BILL")
            amount_due = round(random.uniform(20, 400), 2)
            paid = round(amount_due * random.choice([0, 0.5, 1.0]), 2)
            status = "PAID" if paid >= amount_due else ("PARTIAL" if paid > 0 else "UNPAID")
            s.billing_records[billing_id] = BillingRecord(
                billing_id=billing_id,
                patient_id=patient.patient_id,
                appointment_id=None,
                amount_due=amount_due,
                amount_paid=paid,
                status=status,
                issued_at=datetime.now() - timedelta(days=random.randint(1, 60)),
            )


def _seed_appointments(fake: Faker, s: InMemoryStore, patients: list[Patient], doctors: list[Doctor]) -> None:
    today = date.today()
    statuses_past = [AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW, AppointmentStatus.CANCELLED]

    for patient in patients:
        num_appts = random.randint(1, 3)
        for _ in range(num_appts):
            doctor = random.choice(doctors)
            offset_days = random.randint(-30, 14)
            appt_date = today + timedelta(days=offset_days)
            if appt_date.weekday() > 4:
                appt_date -= timedelta(days=appt_date.weekday() - 4)

            hour = random.choice([9, 10, 11, 13, 14, 15, 16])
            minute = random.choice([0, 30])
            start = time(hour, minute)
            end_minute = minute + 30
            end = time(hour + end_minute // 60, end_minute % 60)

            if offset_days < 0:
                status = random.choices(statuses_past, weights=[0.7, 0.2, 0.1])[0]
            else:
                status = AppointmentStatus.CONFIRMED

            appt_id = s.next_id("A")
            s.appointments[appt_id] = Appointment(
                appointment_id=appt_id,
                patient_id=patient.patient_id,
                doctor_id=doctor.doctor_id,
                date=appt_date,
                start_time=start,
                end_time=end,
                status=status,
                created_at=datetime.now() - timedelta(days=abs(offset_days) + 5),
                updated_at=datetime.now() - timedelta(days=abs(offset_days) + 5),
                reason=fake.sentence(nb_words=6),
            )


def _seed_policies(s: InMemoryStore) -> None:
    for policy_id, title, category, content, tags in POLICY_DOCS:
        s.policy_documents[policy_id] = PolicyDocument(
            policy_id=policy_id, title=title, category=category, content=content, tags=tags
        )


def seed(target_store: InMemoryStore = store) -> InMemoryStore:
    """Populate (or repopulate) `target_store` with deterministic fake data."""
    random.seed(settings.synthetic_data_seed)
    fake = Faker()
    Faker.seed(settings.synthetic_data_seed)

    for attr in (
        "users", "patients", "doctors", "schedules", "appointments",
        "appointment_events", "billing_records", "insurance_records",
        "reports", "approvals", "audit_logs", "policy_documents",
    ):
        getattr(target_store, attr).clear()
    target_store._id_counters.clear()

    doctors = _seed_doctors(fake, target_store)
    patients = _seed_patients(fake, target_store)
    _seed_staff(target_store)
    _seed_insurance(fake, target_store, patients)
    _seed_billing(fake, target_store, patients)
    _seed_appointments(fake, target_store, patients, doctors)
    _seed_policies(target_store)

    return target_store


def reset_store() -> InMemoryStore:
    """Used by tests to get a fresh, deterministic dataset each run."""
    return seed(store)
