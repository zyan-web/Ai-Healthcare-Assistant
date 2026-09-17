"""Communication tool: communication.

Prepares (and optionally "sends" — stubbed in Stage A) authorized
messages to a single recipient. Bulk-communication approval gating
(section 15: >25 recipients needs staff approval) is an orchestration
concern handled by the graph/escalation tool, not by this single-message
tool.
"""
from __future__ import annotations

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.tools import CommunicationArgs, CommunicationData


def _template_appointment_confirmation(ctx: dict) -> tuple[str, str]:
    subject = "Your appointment is confirmed"
    body = (
        f"Hi {ctx.get('patient_name', 'there')}, your appointment with "
        f"{ctx.get('doctor_name', 'your provider')} on {ctx.get('date', '')} at "
        f"{ctx.get('time', '')} is confirmed. Appointment ID: "
        f"{ctx.get('appointment_id', '')}."
    )
    return subject, body


def _template_reminder(ctx: dict) -> tuple[str, str]:
    subject = "Appointment reminder"
    body = (
        f"Hi {ctx.get('patient_name', 'there')}, this is a reminder of your "
        f"upcoming appointment with {ctx.get('doctor_name', 'your provider')} on "
        f"{ctx.get('date', '')} at {ctx.get('time', '')}."
    )
    return subject, body


def _template_cancellation(ctx: dict) -> tuple[str, str]:
    subject = "Appointment cancelled"
    body = (
        f"Hi {ctx.get('patient_name', 'there')}, your appointment "
        f"{ctx.get('appointment_id', '')} on {ctx.get('date', '')} at "
        f"{ctx.get('time', '')} has been cancelled. {ctx.get('note', '')}"
    ).strip()
    return subject, body


def _template_reschedule_confirmation(ctx: dict) -> tuple[str, str]:
    subject = "Appointment rescheduled"
    body = (
        f"Hi {ctx.get('patient_name', 'there')}, your appointment "
        f"{ctx.get('appointment_id', '')} has been moved from "
        f"{ctx.get('previous_date', '')} {ctx.get('previous_time', '')} to "
        f"{ctx.get('date', '')} {ctx.get('time', '')}."
    )
    return subject, body


TEMPLATES = {
    "appointment_confirmation": _template_appointment_confirmation,
    "reminder": _template_reminder,
    "cancellation": _template_cancellation,
    "reschedule_confirmation": _template_reschedule_confirmation,
}


def communication(
    args: CommunicationArgs, s: InMemoryStore = store
) -> ToolResponse[CommunicationData]:
    if args.channel not in ("email", "sms"):
        return ToolResponse.fail(
            ToolErrorCode.VALIDATION_ERROR, f"Unsupported channel '{args.channel}'"
        )

    known_recipient = (
        args.recipient_id in s.patients
        or args.recipient_id in s.doctors
        or args.recipient_id in s.users
    )
    if not known_recipient:
        return ToolResponse.fail(
            ToolErrorCode.NOT_FOUND, f"No recipient found with id {args.recipient_id}"
        )

    if args.template == "custom":
        subject = args.context.get("subject")
        body = args.context.get("body")
        if not body:
            return ToolResponse.fail(
                ToolErrorCode.VALIDATION_ERROR, "custom template requires context.body"
            )
    else:
        builder = TEMPLATES.get(args.template)
        if not builder:
            return ToolResponse.fail(
                ToolErrorCode.UNSUPPORTED,
                f"Unsupported template '{args.template}'. Use one of "
                f"{list(TEMPLATES)} or 'custom'.",
            )
        subject, body = builder(args.context)

    return ToolResponse.ok(
        CommunicationData(
            recipient_id=args.recipient_id,
            channel=args.channel,
            subject=subject,
            body=body,
            sent=bool(args.send),
        )
    )
