"""Web search tool: web_search.

Stage A stub: returns a clearly-labeled placeholder result set instead of
calling a live search API, keeping Stage A free of external network
dependencies and API keys (section 30 notes development uses synthetic/
controlled data). Swap `_run_search` for a real provider (e.g. a hosted
search API) when this moves toward production — the tool's contract
(WebSearchArgs -> WebSearchData) stays the same either way.

This tool is only for *public/external* information. Internal
organization policy must go through policy_rag instead (section 14).
"""
from __future__ import annotations

from app.schemas.common import ToolErrorCode, ToolResponse
from app.schemas.tools import WebSearchArgs, WebSearchData, WebSearchResultItem


def _run_search(query: str, max_results: int) -> list[WebSearchResultItem]:
    # Placeholder implementation — Stage A has no live external search
    # provider wired in yet. Results are synthetic and clearly labeled.
    return [
        WebSearchResultItem(
            title=f"[stub result {i + 1}] {query}",
            url=f"https://example.invalid/search?q={query.replace(' ', '+')}&r={i + 1}",
            snippet=(
                "Stage A web_search stub — no live external provider is "
                "configured yet. Replace app.tools.search._run_search with a "
                "real search API call before relying on this in production."
            ),
        )
        for i in range(max_results)
    ]


def web_search(args: WebSearchArgs) -> ToolResponse[WebSearchData]:
    query = args.query.strip()
    if not query:
        return ToolResponse.fail(ToolErrorCode.VALIDATION_ERROR, "query must not be empty")
    if args.max_results < 1:
        return ToolResponse.fail(ToolErrorCode.VALIDATION_ERROR, "max_results must be >= 1")

    results = _run_search(query, args.max_results)
    return ToolResponse.ok(WebSearchData(query=query, results=results))
