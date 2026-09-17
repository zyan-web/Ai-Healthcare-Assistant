from app.schemas.common import ToolErrorCode
from app.schemas.tools import InsuranceVerifyArgs
from app.tools.insurance import insurance_verify


def test_insurance_verify_active_record(s):
    active_patient_id = next(
        r.patient_id for r in s.insurance_records.values() if r.status == "ACTIVE"
    )

    resp = insurance_verify(InsuranceVerifyArgs(patient_id=active_patient_id), s=s)

    assert resp.success
    assert resp.data.is_active is True
    assert resp.data.record.status == "ACTIVE"


def test_insurance_verify_expired_record_is_not_active(s):
    expired_patient_id = next(
        r.patient_id for r in s.insurance_records.values() if r.status != "ACTIVE"
    )

    resp = insurance_verify(InsuranceVerifyArgs(patient_id=expired_patient_id), s=s)

    assert resp.success
    assert resp.data.is_active is False


def test_insurance_verify_unknown_patient(s):
    resp = insurance_verify(InsuranceVerifyArgs(patient_id="P9999"), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND
