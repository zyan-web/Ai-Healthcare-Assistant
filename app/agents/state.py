"""
LangGraph state (dev order step 6).

Design note: section 6 of the project docs sketches state as a flat dict
of extracted slots (doctor_id, date, selected_slot, confirmed, ...). We
implement that *conversational memory* using the standard message-history
pattern instead of a hand-maintained slot dict: LangGraph persists
`messages` (the full turn-by-turn history, including every ToolMessage
result) across invocations, and the LLM re-reads that history each turn.
So when a user says "11:30" after being shown available slots, the model
already has the doctor/date/slot list in context and can proceed straight
to a confirmation question — the same behavior section 6 describes,
without a second, hand-synced representation of the same facts that could
drift from what the LLM actually saw.

The few extra fields below are bookkeeping that does *not* come from the
LLM: identity the graph is invoked with, and a coarse status for
observability/audit. They are trusted inputs, never something a tool call
argument can overwrite.
"""
from __future__ import annotations

from typing import Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    conversation_id: str
    user_id: str
    role: str
    status: Optional[str]
