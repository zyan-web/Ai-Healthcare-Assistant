"""Report tool: report_generator.

Formats already-verified data (gathered by other tools, e.g. analytics,
billing_lookup, insurance_verify) into a stored report record. It never
computes or invents its own statistics (section 12) — `inputs` must
already contain the verified numbers.
"""
from __future__ import annotations

from datetime import datetime

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.entities import ReportRecord
from app.schemas.tools import ReportGeneratorArgs, ReportGeneratorData


def report_generator(
    args: ReportGeneratorArgs, s: InMemoryStore = store
) -> ToolResponse[ReportGeneratorData]:
    if args.period_start > args.period_end:
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR, "period_start must not be after period_end"
        )
    if not args.inputs:
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR,
            "inputs must contain the verified data gathered from other tools",
        )

    report_id = s.next_id("RPT")
    report = ReportRecord(
        report_id=report_id,
        report_type=args.report_type,
        generated_at=datetime.now(),
        generated_by=args.generated_by,
        period_start=args.period_start,
        period_end=args.period_end,
        content=args.inputs,
    )
    s.reports[report_id] = report
    return ToolResponse.ok(ReportGeneratorData(report=report))
