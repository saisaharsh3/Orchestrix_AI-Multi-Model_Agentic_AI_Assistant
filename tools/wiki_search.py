import requests

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"

def wiki_search(query: str) -> str | None:
    try:
        title = query.replace(" ", "_")
        url = WIKI_API + title
        res = requests.get(url, timeout=5)

        if res.status_code != 200:
            return None

        data = res.json()
        return data.get("extract")

    except Exception:
        return None
