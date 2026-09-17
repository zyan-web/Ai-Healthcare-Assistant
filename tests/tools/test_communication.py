from app.schemas.common import ToolErrorCode
from app.schemas.tools import CommunicationArgs
from app.tools.communication import communication


def test_communication_prepare_only_does_not_mark_sent(s):
    patient_id = next(iter(s.patients))

    resp = communication(
        CommunicationArgs(
            recipient_id=patient_id, channel="email", template="appointment_confirmation",
            context={"patient_name": "Test Patient", "date": "2026-09-21", "time": "11:30"},
            send=False,
        ),
        s=s,
    )

    assert resp.success
    assert resp.data.sent is False
    assert "11:30" in resp.data.body


def test_communication_send_true_marks_sent(s):
    patient_id = next(iter(s.patients))

    resp = communication(
        CommunicationArgs(
            recipient_id=patient_id, channel="sms", template="reminder", send=True,
        ),
        s=s,
    )

    assert resp.success
    assert resp.data.sent is True


def test_communication_unknown_recipient(s):
    resp = communication(
        CommunicationArgs(recipient_id="P9999", channel="email", template="reminder"), s=s
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND


def test_communication_unsupported_template(s):
    patient_id = next(iter(s.patients))

    resp = communication(
        CommunicationArgs(recipient_id=patient_id, channel="email", template="not_a_template"),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.UNSUPPORTED


def test_communication_invalid_channel(s):
    patient_id = next(iter(s.patients))

    resp = communication(
        CommunicationArgs(recipient_id=patient_id, channel="carrier_pigeon", template="reminder"),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
