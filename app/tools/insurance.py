"""Insurance tool: insurance_verify."""
from __future__ import annotations

from datetime import date

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.tools import InsuranceVerifyArgs, InsuranceVerifyData


def insurance_verify(
    args: InsuranceVerifyArgs, s: InMemoryStore = store
) -> ToolResponse[InsuranceVerifyData]:
    if args.patient_id not in s.patients:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No patient found with id {args.patient_id}"
        )
    record = s.insurance_for_patient(args.patient_id)
    is_active = bool(
        record and record.status == "ACTIVE" and record.valid_until >= date.today()
    )
    return ToolResponse.ok(InsuranceVerifyData(record=record, is_active=is_active))
