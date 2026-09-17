from datetime import date, timedelta

from app.schemas.common import ToolErrorCode
from app.schemas.tools import ReportGeneratorArgs
from app.tools.reports import report_generator


def test_report_generator_stores_provided_inputs_verbatim(s):
    inputs = {"appointment_volume": 42, "no_show_rate": 0.1}

    resp = report_generator(
        ReportGeneratorArgs(
            report_type="monthly_operations",
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            generated_by="S003",
            inputs=inputs,
        ),
        s=s,
    )

    assert resp.success
    assert resp.data.report.content == inputs
    assert resp.data.report.report_id in s.reports


def test_report_generator_rejects_empty_inputs(s):
    resp = report_generator(
        ReportGeneratorArgs(
            report_type="monthly_operations",
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            generated_by="S003",
            inputs={},
        ),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR


def test_report_generator_rejects_inverted_period(s):
    resp = report_generator(
        ReportGeneratorArgs(
            report_type="monthly_operations",
            period_start=date.today(),
            period_end=date.today() - timedelta(days=1),
            generated_by="S003",
            inputs={"x": 1},
        ),
        s=s,
    )

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
