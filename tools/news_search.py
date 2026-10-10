from ddgs import DDGS

from core.logger import get_logger

logger = get_logger(__name__)


def news_search(query: str, max_results: int = 3) -> list[str]:
    """DuckDuckGo news search. Returns "title — snippet" strings ([] on failure)."""
    try:
        with DDGS() as ddgs:
            results = ddgs.news(query, max_results=max_results) or []
    except Exception as e:
        logger.warning(f"News search failed: {e}")
        return []
    return [f"{r['title']} — {r['body']}" for r in results if r.get("title") and r.get("body")]
