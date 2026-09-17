"""A minimal stand-in for the Groq chat model, for testing the LangGraph
wiring itself (planner -> tool node -> planner loop) without a live API
key or network access. Structural test only — it does not exercise real
model reasoning.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage


class FakeLLM:
    """Replays a fixed sequence of AIMessage responses, one per .invoke()."""

    def __init__(self, responses: list[AIMessage]):
        self._responses = list(responses)
        self.calls: list[list] = []

    def invoke(self, messages, *args, **kwargs) -> AIMessage:
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("FakeLLM ran out of canned responses")
        return self._responses.pop(0)

    def bind_tools(self, tools):
        return self
