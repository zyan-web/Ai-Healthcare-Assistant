"""
Structural tests for the LangGraph execution loop: planner -> tool node
-> planner, looping until a final answer, and persisting state across
turns via the checkpointer. Uses FakeLLM so these run without network
access or a GROQ_API_KEY.
"""
import json

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agents.graph import build_graph
from tests.agents.fake_llm import FakeLLM


def _config(thread_id="t1"):
    return {"configurable": {"thread_id": thread_id}}


def test_single_tool_call_then_final_answer(s):
    patient_id = next(iter(s.patients))

    fake = FakeLLM(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "appointment_search",
                        "args": {"patient_id": patient_id},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Here are your appointments."),
        ]
    )
    graph = build_graph(llm_with_tools=fake, checkpointer=MemorySaver())

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="What appointments do I have?")],
            "conversation_id": "t1",
            "user_id": patient_id,
            "role": "PATIENT",
            "status": None,
        },
        config=_config(),
    )

    final = result["messages"][-1]
    assert isinstance(final, AIMessage)
    assert not final.tool_calls
    assert final.content == "Here are your appointments."

    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert len(tool_messages) == 1
    payload = json.loads(tool_messages[0].content)
    assert payload["success"] is True
    assert all(a["patient_id"] == patient_id for a in payload["data"]["appointments"])


def test_no_tool_call_returns_final_answer_immediately(s):
    fake = FakeLLM([AIMessage(content="Clinical questions are outside my scope.")])
    graph = build_graph(llm_with_tools=fake, checkpointer=MemorySaver())

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="What medication should I take?")],
            "conversation_id": "t2",
            "user_id": "P0001",
            "role": "PATIENT",
            "status": None,
        },
        config=_config("t2"),
    )

    assert len(result["messages"]) == 2  # human + final AI, no tool round-trip
    assert result["messages"][-1].content == "Clinical questions are outside my scope."


def test_multi_step_tool_chain(s):
    doctor_id = next(iter(s.doctors))

    fake = FakeLLM(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "doctor_schedule", "args": {"doctor_id": doctor_id, "target_date": "2026-09-21"}, "id": "call_1"}
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "availability_search",
                        "args": {"doctor_id": doctor_id, "target_date": "2026-09-21", "time_range": "morning"},
                        "id": "call_2",
                    }
                ],
            ),
            AIMessage(content="Available morning slots found."),
        ]
    )
    graph = build_graph(llm_with_tools=fake, checkpointer=MemorySaver())

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Book me with this doctor next Monday morning.")],
            "conversation_id": "t3",
            "user_id": "P0001",
            "role": "PATIENT",
            "status": None,
        },
        config=_config("t3"),
    )

    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert len(tool_messages) == 2
    assert result["messages"][-1].content == "Available morning slots found."


def test_state_persists_across_turns_via_checkpointer(s):
    patient_id = next(iter(s.patients))
    checkpointer = MemorySaver()

    fake = FakeLLM([AIMessage(content="Got it.")])
    graph = build_graph(llm_with_tools=fake, checkpointer=checkpointer)

    graph.invoke(
        {
            "messages": [HumanMessage(content="Hi, I'm booking an appointment.")],
            "conversation_id": "t4",
            "user_id": patient_id,
            "role": "PATIENT",
            "status": None,
        },
        config=_config("t4"),
    )

    fake._responses.append(AIMessage(content="Continuing our conversation."))
    result = graph.invoke(
        {"messages": [HumanMessage(content="Actually, Monday works.")]},
        config=_config("t4"),
    )

    # The checkpointer should have carried the first turn's messages forward.
    contents = [m.content for m in result["messages"]]
    assert "Hi, I'm booking an appointment." in contents
    assert "Got it." in contents
    assert "Actually, Monday works." in contents
    assert "Continuing our conversation." in contents
