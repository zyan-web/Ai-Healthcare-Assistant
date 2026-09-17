"""Audit tool: audit_log.

Records security/operational events (section 31: "Log important actions
and failures"). Called after consequential actions succeed, fail, or are
denied — never skipped for a denied action, since the denial itself is
the security-relevant event.
"""
from __future__ import annotations

from datetime import datetime

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.entities import AuditLogEntry
from app.schemas.tools import AuditLogArgs, AuditLogData

VALID_RESULTS = {"SUCCESS", "DENIED", "FAILURE"}


def audit_log(args: AuditLogArgs, s: InMemoryStore = store) -> ToolResponse[AuditLogData]:
    if args.result not in VALID_RESULTS:
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR,
            f"Unsupported result '{args.result}'. Use one of {sorted(VALID_RESULTS)}.",
        )

    audit_id = s.next_id("AUD")
    entry = AuditLogEntry(
        audit_id=audit_id,
        actor_id=args.actor_id,
        action=args.action,
        target=args.target,
        result=args.result,
        occurred_at=datetime.now(),
        details=args.details,
    )
    s.audit_logs[audit_id] = entry
    return ToolResponse.ok(AuditLogData(entry=entry))
