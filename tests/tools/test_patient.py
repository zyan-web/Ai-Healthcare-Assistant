from app.schemas.common import ToolErrorCode
from app.schemas.tools import PatientHistoryArgs, PatientProfileArgs, PatientSearchArgs
from app.tools.patient import patient_history, patient_profile, patient_search


def test_patient_search_by_name_fragment(s):
    any_patient = next(iter(s.patients.values()))
    name_fragment = any_patient.full_name.split()[0]

    resp = patient_search(PatientSearchArgs(query=name_fragment), s=s)

    assert resp.success
    assert any(p.patient_id == any_patient.patient_id for p in resp.data.matches)


def test_patient_search_empty_query_is_validation_error(s):
    resp = patient_search(PatientSearchArgs(query="   "), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR


def test_patient_search_no_match_returns_empty_list(s):
    resp = patient_search(PatientSearchArgs(query="zzz-no-such-patient-zzz"), s=s)

    assert resp.success
    assert resp.data.matches == []


def test_patient_profile_found(s):
    patient_id = next(iter(s.patients))

    resp = patient_profile(PatientProfileArgs(patient_id=patient_id), s=s)

    assert resp.success
    assert resp.data.patient.patient_id == patient_id


def test_patient_profile_not_found(s):
    resp = patient_profile(PatientProfileArgs(patient_id="P9999"), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND


def test_patient_history_returns_only_that_patients_appointments(s):
    patient_id = next(iter(s.patients))

    resp = patient_history(PatientHistoryArgs(patient_id=patient_id, limit=20), s=s)

    assert resp.success
    assert all(a.patient_id == patient_id for a in resp.data.appointments)


def test_patient_history_unknown_patient(s):
    resp = patient_history(PatientHistoryArgs(patient_id="P9999"), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.NOT_FOUND
