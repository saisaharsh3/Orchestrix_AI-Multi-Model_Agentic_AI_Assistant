from urllib.parse import quote

import requests

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"


def wiki_search(query: str) -> str | None:
    """Wikipedia page summary for `query`, or None if there is no such page."""
    try:
        res = requests.get(
            WIKI_API + quote(query.strip().replace(" ", "_"), safe=""),
            timeout=5,
            headers={"User-Agent": "Orchestrix/1.0"},
        )
        if res.status_code != 200:
            return None
        return res.json().get("extract")
    except (requests.RequestException, ValueError):
        return None
