from app.schemas.common import ToolErrorCode
from app.schemas.tools import EscalationArgs
from app.tools.escalation import escalation


def test_escalation_creates_pending_approval(s):
    resp = escalation(
        EscalationArgs(
            raised_by="P0001", reason="Patient is asking for medication dosage advice.",
            category="clinical",
        ),
        s=s,
    )

    assert resp.success
    assert resp.data.approval.status == "PENDING"
    assert resp.data.approval.approval_id in s.approvals


def test_escalation_invalid_category(s):
    resp = escalation(
        EscalationArgs(raised_by="P0001", reason="something", category="not_a_category"), s=s
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR


def test_escalation_empty_reason(s):
    resp = escalation(EscalationArgs(raised_by="P0001", reason="  ", category="clinical"), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
