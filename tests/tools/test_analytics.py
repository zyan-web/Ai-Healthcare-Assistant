from datetime import date, timedelta

from app.schemas.common import ToolErrorCode
from app.schemas.tools import AnalyticsArgs
from app.tools.analytics import analytics


def _wide_window():
    return date.today() - timedelta(days=90), date.today() + timedelta(days=90)


def test_appointment_volume_matches_manual_count(s):
    date_from, date_to = _wide_window()

    resp = analytics(
        AnalyticsArgs(metric="appointment_volume", date_from=date_from, date_to=date_to), s=s
    )

    expected = sum(1 for a in s.appointments.values() if date_from <= a.date <= date_to)
    assert resp.success
    assert resp.data.value == expected


def test_no_show_rate_is_between_zero_and_one(s):
    date_from, date_to = _wide_window()

    resp = analytics(
        AnalyticsArgs(metric="no_show_rate", date_from=date_from, date_to=date_to), s=s
    )

    assert resp.success
    assert 0.0 <= resp.data.value <= 1.0


def test_no_show_patients_only_lists_patients_with_a_no_show(s):
    date_from, date_to = _wide_window()

    resp = analytics(
        AnalyticsArgs(metric="no_show_patients", date_from=date_from, date_to=date_to), s=s
    )

    assert resp.success
    from app.schemas.common import AppointmentStatus

    no_show_patient_ids = {
        a.patient_id
        for a in s.appointments.values()
        if a.status == AppointmentStatus.NO_SHOW and date_from <= a.date <= date_to
    }
    assert set(resp.data.patient_ids) == no_show_patient_ids


def test_unsupported_metric_is_rejected(s):
    date_from, date_to = _wide_window()

    resp = analytics(
        AnalyticsArgs(metric="made_up_metric", date_from=date_from, date_to=date_to), s=s
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.UNSUPPORTED


def test_date_range_validation(s):
    resp = analytics(
        AnalyticsArgs(
            metric="appointment_volume", date_from=date.today(),
            date_to=date.today() - timedelta(days=1),
        ),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
