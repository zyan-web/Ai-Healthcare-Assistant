from app.schemas.common import ToolErrorCode
from app.schemas.tools import AuditLogArgs
from app.tools.audit import audit_log


def test_audit_log_records_entry(s):
    resp = audit_log(
        AuditLogArgs(actor_id="P0001", action="BOOK_APPOINTMENT", target="A0001", result="SUCCESS"),
        s=s,
    )

    assert resp.success
    assert resp.data.entry.audit_id in s.audit_logs
    assert resp.data.entry.result == "SUCCESS"


def test_audit_log_records_denied_events_too(s):
    resp = audit_log(
        AuditLogArgs(
            actor_id="P0001", action="VIEW_APPOINTMENTS", target="P2008", result="DENIED",
            details={"reason": "cross-patient access denied"},
        ),
        s=s,
    )

    assert resp.success
    assert resp.data.entry.result == "DENIED"


def test_audit_log_invalid_result(s):
    resp = audit_log(
        AuditLogArgs(actor_id="P0001", action="X", result="MAYBE"), s=s
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
