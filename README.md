# AI Healthcare Operations & Administration Agent — Stage A

Standalone agent (no FastAPI, no database, no auth/RBAC yet). Per the
project's development order, this is built and tested first; the FastAPI
security boundary, PostgreSQL persistence, JWT, RBAC, approvals, and audit
storage are added only after this is stable.

## Status

Done (dev order steps 1-8):

- [`app/schemas/tools.py`](app/schemas/tools.py) — Args/Data contract for every tool.
- [`app/data/seed.py`](app/data/seed.py) — deterministic synthetic data (patients, doctors, schedules, appointments, billing, insurance, policy docs).
- [`app/tools/`](app/tools/) — all 19 tools from the spec, each a pure function returning a `ToolResponse` envelope.
- [`tests/tools/`](tests/tools/) — unit tests for every tool (happy path + validation/not-found/conflict cases).
- [`app/agents/`](app/agents/) — LangChain/Groq LLM wiring, LangGraph state, tool registry, system prompt, and the planner/tool execution loop.
- [`tests/agents/test_graph.py`](tests/agents/test_graph.py) — structural tests of the graph loop using a fake LLM (no API key needed).

Not yet built (steps 9 onward): the explicit stateful booking/reschedule/
cancel *flows* rely on the LLM following the system prompt today rather
than a hand-coded flow graph; billing/insurance/analytics workflows,
richer policy RAG (currently keyword match, not embeddings), and
everything from FastAPI onward (steps 17-24).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY
```

## Run the tests

```bash
source .venv/bin/activate
pytest -q
```

Tool and graph-wiring tests run without a Groq API key (the graph tests
use a stub LLM to verify the planner/tool-node loop mechanics).

## Try the agent

```bash
source .venv/bin/activate
python -m app.main
```

Requires `GROQ_API_KEY` in `.env`. Seeds fresh synthetic data each run,
picks a sample patient to act as, and starts a terminal chat loop.

some new updates are under way