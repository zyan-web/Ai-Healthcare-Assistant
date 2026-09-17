"""Patient tools: patient_search, patient_profile, patient_history.

Note: in Stage A there is no permission engine yet, so these functions
return whatever matches the query. Stage B wraps every tool call with
`authorize(user, tool_name, scope, arguments)` (section 17) before it
ever reaches here — patient_search/profile/history are exactly the tools
that must be scoped to OWN_DATA for PATIENT callers at that point.
"""
from __future__ import annotations

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.tools import (
    PatientHistoryArgs,
    PatientHistoryData,
    PatientProfileArgs,
    PatientProfileData,
    PatientSearchArgs,
    PatientSearchData,
)


def patient_search(
    args: PatientSearchArgs, s: InMemoryStore = store
) -> ToolResponse[PatientSearchData]:
    q = args.query.strip().lower()
    if not q:
        return ToolResponse.fail(ToolErrorCode.VALIDATION_ERROR, "query must not be empty")

    matches = [
        p
        for p in s.patients.values()
        if q in p.patient_id.lower()
        or q in p.full_name.lower()
        or q in p.email.lower()
        or q in p.phone.lower()
    ]
    return ToolResponse.ok(PatientSearchData(matches=matches))


def patient_profile(
    args: PatientProfileArgs, s: InMemoryStore = store
) -> ToolResponse[PatientProfileData]:
    patient = s.patients.get(args.patient_id)
    if not patient:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No patient found with id {args.patient_id}"
        )
    return ToolResponse.ok(PatientProfileData(patient=patient))


def patient_history(
    args: PatientHistoryArgs, s: InMemoryStore = store
) -> ToolResponse[PatientHistoryData]:
    if args.patient_id not in s.patients:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No patient found with id {args.patient_id}"
        )
    appointments = sorted(
        s.appointments_for_patient(args.patient_id),
        key=lambda a: (a.date, a.start_time),
        reverse=True,
    )[: args.limit]
    return ToolResponse.ok(PatientHistoryData(appointments=appointments))
