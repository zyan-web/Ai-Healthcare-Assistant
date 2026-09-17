"""Analytics tool: operational metrics computed from verified store data.

The agent must never invent statistics (section 12) — every number here is
derived directly from the appointment records in the store.
"""
from __future__ import annotations

from collections import Counter

from app.data.store import InMemoryStore, store
from app.schemas.common import AppointmentStatus, ToolErrorCode, ToolResponse
from app.schemas.tools import AnalyticsArgs, AnalyticsData

SUPPORTED_METRICS = {"no_show_rate", "appointment_volume", "no_show_patients"}


def _appointments_in_period(s: InMemoryStore, args: AnalyticsArgs):
    for a in s.appointments.values():
        if not (args.date_from <= a.date <= args.date_to):
            continue
        if args.doctor_id and a.doctor_id != args.doctor_id:
            continue
        yield a


def analytics(args: AnalyticsArgs, s: InMemoryStore = store) -> ToolResponse[AnalyticsData]:
    if args.metric not in SUPPORTED_METRICS:
        return ToolResponse.fail(
            ToolErrorCode.UNSUPPORTED,
            f"Unsupported metric '{args.metric}'. Use one of {sorted(SUPPORTED_METRICS)}.",
        )
    if args.date_from > args.date_to:
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR, "date_from must not be after date_to"
        )

    appts = list(_appointments_in_period(s, args))

    if args.metric == "appointment_volume":
        breakdown = dict(Counter(a.status.value for a in appts))
        return ToolResponse.ok(
            AnalyticsData(
                metric=args.metric, date_from=args.date_from, date_to=args.date_to,
                value=len(appts), breakdown=breakdown,
            )
        )

    if args.metric == "no_show_rate":
        occurred = [
            a for a in appts
            if a.status in (AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW)
        ]
        no_shows = [a for a in occurred if a.status == AppointmentStatus.NO_SHOW]
        rate = round(len(no_shows) / len(occurred), 4) if occurred else 0.0
        return ToolResponse.ok(
            AnalyticsData(
                metric=args.metric, date_from=args.date_from, date_to=args.date_to,
                value=rate,
                breakdown={"no_show_count": len(no_shows), "occurred_count": len(occurred)},
            )
        )

    # no_show_patients
    patient_ids = sorted({a.patient_id for a in appts if a.status == AppointmentStatus.NO_SHOW})
    return ToolResponse.ok(
        AnalyticsData(
            metric=args.metric, date_from=args.date_from, date_to=args.date_to,
            patient_ids=patient_ids,
        )
    )
