"""
The LangGraph execution loop (dev order step 8): planner -> tool
execution -> observe -> decide next step, looping until the model has a
final answer with no more tool calls (section 5 / section 3 diagram).

Stage A persists conversation state with an in-memory checkpointer keyed
by `conversation_id`, so multi-turn flows (pick a doctor, then a slot,
then confirm) work across separate `invoke` calls without a database.
Step 18 swaps this for a Postgres-backed checkpointer; nothing else here
needs to change when that happens.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.llm import build_llm
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.state import AgentState
from app.agents.tools_registry import get_tools


def _agent_node_factory(llm_with_tools):
    def agent_node(state: AgentState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    return agent_node


def build_graph(llm_with_tools=None, checkpointer=None):
    """Build the compiled LangGraph app.

    `llm_with_tools` is injectable so tests can pass a stub model instead
    of hitting the real Groq API (see tests/agents/test_graph.py).
    """
    tools = get_tools()
    if llm_with_tools is None:
        llm_with_tools = build_llm().bind_tools(tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node_factory(llm_with_tools))
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer or MemorySaver())
