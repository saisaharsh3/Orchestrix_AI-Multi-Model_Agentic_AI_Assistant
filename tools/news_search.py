from duckduckgo_search import DDGS

def news_search(query: str, max_results: int = 3):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.news(query, max_results=max_results):
            if r.get("title") and r.get("body"):
                results.append(f"{r['title']} — {r['body']}")
    return results
