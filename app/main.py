"""
Stage A standalone agent CLI.

No FastAPI, no auth, no RBAC yet — this is the terminal harness for
building and thoroughly testing the agent/tool loop itself before any of
that is added (project docs, section 29). Requires GROQ_API_KEY in .env.

Usage:
    python -m app.main
"""
from __future__ import annotations

import sys
import uuid

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.graph import build_graph
from app.data.seed import reset_store
from app.schemas.common import Role


def main() -> None:
    print("Seeding synthetic data...")
    store = reset_store()

    print("\nSample patient IDs:", ", ".join(list(store.patients)[:5]))
    print("Sample doctor IDs:  ", ", ".join(list(store.doctors)[:5]))

    user_id = input("\nActing as patient_id (blank = first sample patient): ").strip()
    if not user_id:
        user_id = next(iter(store.patients))
    role = Role.PATIENT.value

    try:
        graph = build_graph()
    except RuntimeError as exc:
        print(f"\n{exc}", file=sys.stderr)
        sys.exit(1)

    conversation_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": conversation_id}}

    print(f"\nStage A healthcare operations agent — acting as {user_id} ({role})")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        result = graph.invoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "status": None,
            },
            config=config,
        )

        final = result["messages"][-1]
        if isinstance(final, AIMessage):
            print(f"Agent: {final.content}\n")


if __name__ == "__main__":
    main()
