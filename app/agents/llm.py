"""LLM wiring (dev order step 5): LangChain -> Groq-hosted Llama/Qwen model."""
from __future__ import annotations

from langchain_groq import ChatGroq

from app.agents.tools_registry import get_tools
from app.core.config import settings


def build_llm() -> ChatGroq:
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and fill it in "
            "before running the live agent (tests use a stub LLM and don't "
            "need this)."
        )
    return ChatGroq(model=settings.agent_model, api_key=settings.groq_api_key, temperature=0)


def build_llm_with_tools():
    return build_llm().bind_tools(get_tools())
