"""
In-memory stand-in for PostgreSQL during Stage A.

Tools depend only on this module's interface (get/list/insert/update by
id), so swapping it for a real SQLAlchemy-backed store in Stage B should
not require changing tool logic — only this module.
"""
from __future__ import annotations

from typing import Optional

from app.schemas.entities import (
    Appointment,
    AppointmentEvent,
    ApprovalRequest,
    AuditLogEntry,
    BillingRecord,
    Doctor,
    DoctorSchedule,
    InsuranceRecord,
    Patient,
    PolicyDocument,
    ReportRecord,
    User,
)


class InMemoryStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.patients: dict[str, Patient] = {}
        self.doctors: dict[str, Doctor] = {}
        self.schedules: dict[str, DoctorSchedule] = {}
        self.appointments: dict[str, Appointment] = {}
        self.appointment_events: dict[str, AppointmentEvent] = {}
        self.billing_records: dict[str, BillingRecord] = {}
        self.insurance_records: dict[str, InsuranceRecord] = {}
        self.reports: dict[str, ReportRecord] = {}
        self.approvals: dict[str, ApprovalRequest] = {}
        self.audit_logs: dict[str, AuditLogEntry] = {}
        self.policy_documents: dict[str, PolicyDocument] = {}
        self._id_counters: dict[str, int] = {}

    def next_id(self, prefix: str) -> str:
        self._id_counters[prefix] = self._id_counters.get(prefix, 0) + 1
        return f"{prefix}{self._id_counters[prefix]:04d}"

    # -- convenience lookups used across multiple tools --

    def appointments_for_patient(self, patient_id: str) -> list[Appointment]:
        return [a for a in self.appointments.values() if a.patient_id == patient_id]

    def appointments_for_doctor_on_date(self, doctor_id: str, target_date) -> list[Appointment]:
        return [
            a
            for a in self.appointments.values()
            if a.doctor_id == doctor_id
            and a.date == target_date
            and a.status.value not in ("CANCELLED",)
        ]

    def insurance_for_patient(self, patient_id: str) -> Optional[InsuranceRecord]:
        for record in self.insurance_records.values():
            if record.patient_id == patient_id:
                return record
        return None

    def billing_for_patient(self, patient_id: str) -> list[BillingRecord]:
        return [b for b in self.billing_records.values() if b.patient_id == patient_id]


store = InMemoryStore()
