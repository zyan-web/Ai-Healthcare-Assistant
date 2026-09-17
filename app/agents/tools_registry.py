"""
Wraps every tool in app/tools/* as a LangChain StructuredTool so the LLM
can propose calls to them (dev order step 5 depends on this; the tools
themselves were already built and unit-tested in steps 1-4).

Each wrapper: validates the LLM's proposed arguments against the tool's
Args schema (StructuredTool does this via `args_schema` before our code
ever runs), calls the existing, already-tested tool function, and returns
the `ToolResponse` envelope as JSON. The LLM never gets a raw exception —
only a structured success/error payload (section 5, step 8).
"""
from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.schemas.tools import (
    AnalyticsArgs,
    AppointmentCancelArgs,
    AppointmentCreateArgs,
    AppointmentRescheduleArgs,
    AppointmentSearchArgs,
    AvailabilitySearchArgs,
    BillingLookupArgs,
    CommunicationArgs,
    DoctorScheduleArgs,
    DoctorSearchArgs,
    EscalationArgs,
    InsuranceVerifyArgs,
    PatientHistoryArgs,
    PatientProfileArgs,
    PatientSearchArgs,
    PolicyRagArgs,
    ReportGeneratorArgs,
    WebSearchArgs,
)
from app.tools.analytics import analytics
from app.tools.appointments import (
    appointment_cancel,
    appointment_create,
    appointment_reschedule,
    appointment_search,
)
from app.tools.audit import audit_log
from app.schemas.tools import AuditLogArgs
from app.tools.billing import billing_lookup
from app.tools.calendar import availability_search, doctor_schedule, doctor_search
from app.tools.communication import communication
from app.tools.escalation import escalation
from app.tools.insurance import insurance_verify
from app.tools.patient import patient_history, patient_profile, patient_search
from app.tools.rag import policy_rag
from app.tools.reports import report_generator
from app.tools.search import web_search

# (tool name, description shown to the LLM, args schema, underlying function)
# Descriptions mirror the "Purpose"/"Example" columns in project docs section 4.
TOOL_SPECS: list[tuple[str, str, type[BaseModel], callable]] = [
    (
        "patient_search",
        "Find a patient using a permitted identifier: name, patient_id, email, "
        "or phone fragment. Example: find P1004.",
        PatientSearchArgs,
        patient_search,
    ),
    (
        "patient_profile",
        "Retrieve a patient's authorized administrative profile by patient_id.",
        PatientProfileArgs,
        patient_profile,
    ),
    (
        "patient_history",
        "Retrieve a patient's authorized appointment history by patient_id.",
        PatientHistoryArgs,
        patient_history,
    ),
    (
        "doctor_search",
        "Find a provider by name or specialty fragment. Example: find Dr. Ahmed, "
        "or find a cardiologist.",
        DoctorSearchArgs,
        doctor_search,
    ),
    (
        "doctor_schedule",
        "Retrieve a doctor's working schedule for a specific date, including "
        "whether that date is a working day for them.",
        DoctorScheduleArgs,
        doctor_schedule,
    ),
    (
        "appointment_search",
        "Find appointments by any combination of patient_id, doctor_id, date "
        "range, and status. Example: P1004's appointments tomorrow.",
        AppointmentSearchArgs,
        appointment_search,
    ),
    (
        "availability_search",
        "Find currently bookable time slots for a doctor on a date, optionally "
        "restricted to a time_range (morning | afternoon | evening | all_day). "
        "Always call this — and re-call it immediately before booking — rather "
        "than assuming a slot is still free.",
        AvailabilitySearchArgs,
        availability_search,
    ),
    (
        "appointment_create",
        "Book a new appointment. CONSEQUENTIAL: only call this after the user "
        "has explicitly confirmed the doctor, date, and time. This tool itself "
        "re-checks the slot and returns a CONFLICT error (never a false "
        "success) if it was taken in the meantime — if that happens, search "
        "availability again and offer alternatives instead of claiming success.",
        AppointmentCreateArgs,
        appointment_create,
    ),
    (
        "appointment_cancel",
        "Cancel an existing appointment by appointment_id. CONSEQUENTIAL: "
        "confirm with the user first, and check policy_rag for the "
        "cancellation policy when timing/fees may apply.",
        AppointmentCancelArgs,
        appointment_cancel,
    ),
    (
        "appointment_reschedule",
        "Move an existing appointment to a new date/time. CONSEQUENTIAL: "
        "confirm with the user first. This tool re-checks the new slot and "
        "returns CONFLICT rather than a false success if it's no longer free.",
        AppointmentRescheduleArgs,
        appointment_reschedule,
    ),
    (
        "billing_lookup",
        "Retrieve a patient's billing records and total outstanding balance.",
        BillingLookupArgs,
        billing_lookup,
    ),
    (
        "insurance_verify",
        "Verify a patient's insurance status (active/inactive/expired).",
        InsuranceVerifyArgs,
        insurance_verify,
    ),
    (
        "analytics",
        "Calculate an operational metric over a date range: "
        "'appointment_volume', 'no_show_rate', or 'no_show_patients'. Never "
        "estimate these numbers yourself — always call this tool.",
        AnalyticsArgs,
        analytics,
    ),
    (
        "policy_rag",
        "Retrieve INTERNAL administrative policy text relevant to a query "
        "(cancellation windows, refund rules, working hours, communication "
        "rules, escalation procedures). Use this, not web_search, for "
        "questions about this organization's own rules.",
        PolicyRagArgs,
        policy_rag,
    ),
    (
        "web_search",
        "Retrieve permitted PUBLIC/EXTERNAL information not stored in "
        "internal policy (e.g. public information about a provider). Do not "
        "use this for internal policy questions — use policy_rag instead.",
        WebSearchArgs,
        web_search,
    ),
    (
        "communication",
        "Prepare (and, if send=true, send) an authorized message to one "
        "recipient using a template (appointment_confirmation, reminder, "
        "cancellation, reschedule_confirmation, or custom). For messages to "
        "more than 25 recipients, call escalation for approval first instead "
        "of sending directly.",
        CommunicationArgs,
        communication,
    ),
    (
        "report_generator",
        "Generate a structured operational report from data you have already "
        "gathered and verified via other tools (pass it as `inputs`). Never "
        "invents or estimates figures itself.",
        ReportGeneratorArgs,
        report_generator,
    ),
    (
        "escalation",
        "Route a request to a human: clinical/medical requests, sensitive "
        "data requests, policy conflicts, or bulk actions needing approval. "
        "Use this instead of answering clinical questions yourself.",
        EscalationArgs,
        escalation,
    ),
    (
        "audit_log",
        "Record a security/operational event. Call this after consequential "
        "actions succeed, fail, or are denied.",
        AuditLogArgs,
        audit_log,
    ),
]


def _make_tool(name: str, description: str, args_model: type[BaseModel], fn) -> StructuredTool:
    def wrapper(**kwargs) -> str:
        args = args_model(**kwargs)
        response = fn(args)
        return json.dumps(response.model_dump(mode="json"))

    wrapper.__name__ = name
    return StructuredTool.from_function(
        func=wrapper,
        name=name,
        description=description,
        args_schema=args_model,
    )


def get_tools() -> list[StructuredTool]:
    return [_make_tool(*spec) for spec in TOOL_SPECS]


CONSEQUENTIAL_TOOLS = {
    "appointment_create",
    "appointment_cancel",
    "appointment_reschedule",
}
