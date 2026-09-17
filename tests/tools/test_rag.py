from app.schemas.common import ToolErrorCode
from app.schemas.tools import PolicyRagArgs
from app.tools.rag import policy_rag


def test_policy_rag_finds_cancellation_policy(s):
    resp = policy_rag(PolicyRagArgs(query="cancellation fee no-show"), s=s)

    assert resp.success
    assert any(doc.policy_id == "cancellation_policy" for doc in resp.data.results)


def test_policy_rag_respects_top_k(s):
    resp = policy_rag(PolicyRagArgs(query="policy scheduling billing communication", top_k=2), s=s)

    assert resp.success
    assert len(resp.data.results) <= 2


def test_policy_rag_no_match_returns_empty_results(s):
    resp = policy_rag(PolicyRagArgs(query="xylophone quantum teapot"), s=s)

    assert resp.success
    assert resp.data.results == []


def test_policy_rag_empty_query_is_validation_error(s):
    resp = policy_rag(PolicyRagArgs(query="  "), s=s)

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
