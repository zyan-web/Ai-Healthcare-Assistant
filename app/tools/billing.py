"""Billing tool: billing_lookup."""
from __future__ import annotations

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.tools import BillingLookupArgs, BillingLookupData


def billing_lookup(
    args: BillingLookupArgs, s: InMemoryStore = store
) -> ToolResponse[BillingLookupData]:
    if args.patient_id not in s.patients:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No patient found with id {args.patient_id}"
        )
    records = s.billing_for_patient(args.patient_id)
    total_outstanding = round(
        sum(max(r.amount_due - r.amount_paid, 0.0) for r in records), 2
    )
    return ToolResponse.ok(
        BillingLookupData(records=records, total_outstanding=total_outstanding)
    )
