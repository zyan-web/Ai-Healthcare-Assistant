from app.schemas.common import ToolErrorCode
from app.schemas.tools import WebSearchArgs
from app.tools.search import web_search


def test_web_search_returns_requested_number_of_results():
    resp = web_search(WebSearchArgs(query="clinic accreditation status", max_results=2))

    assert resp.success
    assert len(resp.data.results) == 2


def test_web_search_empty_query_is_validation_error():
    resp = web_search(WebSearchArgs(query=""))

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR


def test_web_search_invalid_max_results_is_validation_error():
    resp = web_search(WebSearchArgs(query="anything", max_results=0))

    assert not resp.success
    assert resp.error.code == ToolErrorCode.VALIDATION_ERROR
