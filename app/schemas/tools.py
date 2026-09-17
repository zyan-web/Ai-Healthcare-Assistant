"""
Tool contracts (step 1 of the dev order): one Args/Data pair per tool in
the complete tool set (project docs, section 4). Every tool function takes
its `*Args` model and returns `ToolResponse[*Data]`.

These are deliberately narrow and typed — the LLM proposes arguments that
must validate against these schemas before any deterministic code runs
(section 5, step 5). No tool accepts raw SQL, free-form code, or credentials.
"""
from __future__ import annotations

from datetime import date, time
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import AppointmentStatus
from app.schemas.entities import (
    Appointment,
    ApprovalRequest,
    AuditLogEntry,
    BillingRecord,
    Doctor,
    DoctorSchedule,
    InsuranceRecord,
    Patient,
    PolicyDocument,
    ReportRecord,
)

# ---- patient_search ----


class PatientSearchArgs(BaseModel):
    query: str  # name, patient_id, email or phone fragment


class PatientSearchData(BaseModel):
    matches: list[Patient]


# ---- patient_profile ----


class PatientProfileArgs(BaseModel):
    patient_id: str


class PatientProfileData(BaseModel):
    patient: Patient


# ---- patient_history ----


class PatientHistoryArgs(BaseModel):
    patient_id: str
    limit: int = 20


class PatientHistoryData(BaseModel):
    appointments: list[Appointment]


# ---- doctor_search ----


class DoctorSearchArgs(BaseModel):
    query: str  # name or specialty fragment


class DoctorSearchData(BaseModel):
    matches: list[Doctor]


# ---- doctor_schedule ----


class DoctorScheduleArgs(BaseModel):
    doctor_id: str
    target_date: date


class DoctorScheduleData(BaseModel):
    doctor_id: str
    target_date: date
    schedule: DoctorSchedule
    is_working_day: bool


# ---- appointment_search ----


class AppointmentSearchArgs(BaseModel):
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[AppointmentStatus] = None


class AppointmentSearchData(BaseModel):
    appointments: list[Appointment]


# ---- availability_search ----


class TimeRange(BaseModel):
    label: str  # "morning" | "afternoon" | "evening" | "all_day"
    start: time
    end: time


class AvailabilitySearchArgs(BaseModel):
    doctor_id: str
    target_date: date
    time_range: str = "all_day"  # morning | afternoon | evening | all_day


class AvailabilitySearchData(BaseModel):
    doctor_id: str
    target_date: date
    available_slots: list[time]


# ---- appointment_create ----


class AppointmentCreateArgs(BaseModel):
    patient_id: str
    doctor_id: str
    target_date: date
    start_time: time
    reason: Optional[str] = None


class AppointmentCreateData(BaseModel):
    appointment: Appointment


# ---- appointment_cancel ----


class AppointmentCancelArgs(BaseModel):
    appointment_id: str
    cancelled_by: str
    reason: Optional[str] = None


class AppointmentCancelData(BaseModel):
    appointment: Appointment


# ---- appointment_reschedule ----


class AppointmentRescheduleArgs(BaseModel):
    appointment_id: str
    new_date: date
    new_start_time: time
    rescheduled_by: str


class AppointmentRescheduleData(BaseModel):
    appointment: Appointment
    previous_date: date
    previous_start_time: time


# ---- billing_lookup ----


class BillingLookupArgs(BaseModel):
    patient_id: str


class BillingLookupData(BaseModel):
    records: list[BillingRecord]
    total_outstanding: float


# ---- insurance_verify ----


class InsuranceVerifyArgs(BaseModel):
    patient_id: str


class InsuranceVerifyData(BaseModel):
    record: Optional[InsuranceRecord]
    is_active: bool


# ---- analytics ----


class AnalyticsArgs(BaseModel):
    metric: str  # "no_show_rate" | "appointment_volume" | "no_show_patients"
    date_from: date
    date_to: date
    doctor_id: Optional[str] = None


class AnalyticsData(BaseModel):
    metric: str
    date_from: date
    date_to: date
    value: float | int | None = None
    patient_ids: list[str] = []
    breakdown: dict = {}


# ---- policy_rag ----


class PolicyRagArgs(BaseModel):
    query: str
    top_k: int = 3


class PolicyRagData(BaseModel):
    query: str
    results: list[PolicyDocument]


# ---- web_search ----


class WebSearchArgs(BaseModel):
    query: str
    max_results: int = 3


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchData(BaseModel):
    query: str
    results: list[WebSearchResultItem]


# ---- communication ----


class CommunicationArgs(BaseModel):
    recipient_id: str
    channel: str  # "email" | "sms"
    template: str  # e.g. "appointment_confirmation", "reminder", "cancellation"
    context: dict = {}
    send: bool = False  # False => prepare only, True => prepare + send


class CommunicationData(BaseModel):
    recipient_id: str
    channel: str
    subject: Optional[str]
    body: str
    sent: bool


# ---- report_generator ----


class ReportGeneratorArgs(BaseModel):
    report_type: str  # "monthly_operations"
    period_start: date
    period_end: date
    generated_by: str
    inputs: dict  # verified data gathered from other tools (analytics, billing, insurance)


class ReportGeneratorData(BaseModel):
    report: ReportRecord


# ---- escalation ----


class EscalationArgs(BaseModel):
    raised_by: str
    reason: str
    category: str  # "clinical" | "sensitive_data" | "policy_conflict" | "other"
    context: dict = {}


class EscalationData(BaseModel):
    approval: ApprovalRequest


# ---- audit_log ----


class AuditLogArgs(BaseModel):
    actor_id: str
    action: str
    target: Optional[str] = None
    result: str = "SUCCESS"
    details: dict = {}


class AuditLogData(BaseModel):
    entry: AuditLogEntry
