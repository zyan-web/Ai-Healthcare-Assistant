"""Policy RAG tool: policy_rag.

Stage A retrieval is a scored keyword match over the synthetic policy
documents (app/data/seed.py) — no embeddings/vector store yet. Section 29
step 12 upgrades this to real embeddings + pgvector/Qdrant once the agent
loop above it is stable; the tool's contract (PolicyRagArgs -> PolicyRagData)
does not need to change when that happens.

This tool answers questions about *internal* policy only. It must not be
used for public/external information — that is web_search's job
(section 14).
"""
from __future__ import annotations

import re

from app.data.store import InMemoryStore, store
from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.entities import PolicyDocument
from app.schemas.tools import PolicyRagArgs, PolicyRagData

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _score(query_tokens: set[str], doc: PolicyDocument) -> int:
    doc_tokens = _tokenize(doc.title) | _tokenize(doc.content) | {t.lower() for t in doc.tags}
    return len(query_tokens & doc_tokens)


def policy_rag(args: PolicyRagArgs, s: InMemoryStore = store) -> ToolResponse[PolicyRagData]:
    query_tokens = _tokenize(args.query)
    if not query_tokens:
        return ToolResponse.fail(ToolErrorCode.VALIDATION_ERROR, "query must not be empty")

    scored = [(doc, _score(query_tokens, doc)) for doc in s.policy_documents.values()]
    scored = [(doc, score) for doc, score in scored if score > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    results = [doc for doc, _ in scored[: args.top_k]]
    return ToolResponse.ok(PolicyRagData(query=args.query, results=results))
