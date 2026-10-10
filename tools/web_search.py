from ddgs import DDGS

from core.logger import get_logger

logger = get_logger(__name__)


def web_search(query: str, max_results: int = 5) -> list[str]:
    """DuckDuckGo text search. Returns "title\nsnippet" strings ([] on failure)."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results) or []
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return []

    items = []
    for r in results:
        title = (r.get("title") or "").strip()
        body = (r.get("body") or "").strip()
        if title or body:
            items.append(f"{title}\n{body}".strip())
    return items
