"""Escalation tool: escalation.

Used both for human-in-the-loop approvals (e.g. bulk communication,
sensitive report distribution) and for routing clinical/out-of-scope
requests to a human (section 15). Creates a PENDING ApprovalRequest;
resolving it (approve/reject) is a separate Stage B concern
(POST /api/approvals/{id}/approve|reject, section 19).
"""
from __future__ import annotations

from datetime import datetime

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.entities import ApprovalRequest
from app.schemas.tools import EscalationArgs, EscalationData

VALID_CATEGORIES = {"clinical", "sensitive_data", "policy_conflict", "bulk_action", "other"}


def escalation(args: EscalationArgs, s: InMemoryStore = store) -> ToolResponse[EscalationData]:
    if args.category not in VALID_CATEGORIES:
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR,
            f"Unsupported category '{args.category}'. Use one of {sorted(VALID_CATEGORIES)}.",
        )
    if not args.reason.strip():
        return ToolResponse.fail(ToolErrorCode.VALIDATION_ERROR, "reason must not be empty")

    approval_id = s.next_id("APR")
    approval = ApprovalRequest(
        approval_id=approval_id,
        requested_by=args.raised_by,
        action_type=args.category,
        payload={"reason": args.reason, **args.context},
        status="PENDING",
        created_at=datetime.now(),
    )
    s.approvals[approval_id] = approval
    return ToolResponse.ok(EscalationData(approval=approval))
