from ddgs import DDGS

def web_search(query: str, max_results: int = 5) -> str:
    """
    Perform a DuckDuckGo web search and return summarized results.
    """
    results_text = []

    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)

        for i, r in enumerate(results, start=1):
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            if title or body:
                results_text.append(f"{i}. {title}\n{body}")

    return "\n\n".join(results_text)
