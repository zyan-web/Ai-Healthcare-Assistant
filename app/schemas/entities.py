"""
Entity models corresponding to the data model in the project docs
(section 21). In Stage A these are held in-memory (app/data/store.py); in
Stage B they map onto PostgreSQL tables.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import AppointmentStatus, Role


class User(BaseModel):
    user_id: str
    role: Role
    email: EmailStr
    display_name: str
    active: bool = True


class Patient(BaseModel):
    patient_id: str
    user_id: str
    full_name: str
    date_of_birth: date
    phone: str
    email: EmailStr
    insurance_id: Optional[str] = None


class Doctor(BaseModel):
    doctor_id: str
    full_name: str
    specialty: str
    department: str
    email: EmailStr


class WorkingHours(BaseModel):
    day_of_week: int  # 0=Monday .. 6=Sunday
    start_time: time
    end_time: time


class DoctorSchedule(BaseModel):
    doctor_id: str
    working_hours: list[WorkingHours]
    slot_minutes: int = 30


class Appointment(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
    reason: Optional[str] = None


class AppointmentEvent(BaseModel):
    event_id: str
    appointment_id: str
    event_type: str  # CREATED | RESCHEDULED | CANCELLED
    occurred_at: datetime
    details: dict = Field(default_factory=dict)


class BillingRecord(BaseModel):
    billing_id: str
    patient_id: str
    appointment_id: Optional[str] = None
    amount_due: float
    amount_paid: float
    currency: str = "USD"
    status: str  # PAID | UNPAID | PARTIAL | OVERDUE
    issued_at: datetime


class InsuranceRecord(BaseModel):
    insurance_id: str
    patient_id: str
    provider_name: str
    policy_number: str
    status: str  # ACTIVE | INACTIVE | EXPIRED | PENDING
    valid_until: date


class ReportRecord(BaseModel):
    report_id: str
    report_type: str
    generated_at: datetime
    generated_by: str
    period_start: date
    period_end: date
    content: dict


class ApprovalRequest(BaseModel):
    approval_id: str
    requested_by: str
    action_type: str
    payload: dict
    status: str = "PENDING"  # PENDING | APPROVED | REJECTED
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class AuditLogEntry(BaseModel):
    audit_id: str
    actor_id: str
    action: str
    target: Optional[str] = None
    result: str  # SUCCESS | DENIED | FAILURE
    occurred_at: datetime
    details: dict = Field(default_factory=dict)


class PolicyDocument(BaseModel):
    policy_id: str
    title: str
    category: str
    content: str
    tags: list[str] = Field(default_factory=list)
