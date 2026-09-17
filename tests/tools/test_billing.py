from app.schemas.common import ToolErrorCode
from app.schemas.tools import BillingLookupArgs
from app.tools.billing import billing_lookup


def test_billing_lookup_computes_outstanding_total(s):
    patient_id = next(
        p for p, records in _by_patient(s).items() if records
    )

    resp = billing_lookup(BillingLookupArgs(patient_id=patient_id), s=s)

    assert resp.success
    expected = round(sum(max(r.amount_due - r.amount_paid, 0.0) for r in resp.data.records), 2)
    assert resp.data.total_outstanding == expected


def test_billing_lookup_unknown_patient(s):
    resp = billing_lookup(BillingLookupArgs(patient_id="P9999"), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND


def test_billing_lookup_no_records_is_zero_outstanding(s):
    patient_id = next(p for p, records in _by_patient(s).items() if not records)

    resp = billing_lookup(BillingLookupArgs(patient_id=patient_id), s=s)

    assert resp.success
    assert resp.data.records == []
    assert resp.data.total_outstanding == 0.0


def _by_patient(s):
    grouped: dict[str, list] = {p: [] for p in s.patients}
    for record in s.billing_records.values():
        grouped[record.patient_id].append(record)
    return grouped
