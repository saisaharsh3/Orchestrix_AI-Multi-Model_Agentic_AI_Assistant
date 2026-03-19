"""
url_tool.py - URL summarization and price tracking
Uses rotating headers and session to avoid Amazon bot detection.
Install: pip install requests beautifulsoup4
"""

import os
import json
import re
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

PRICE_TRACK_FILE = "data/tracked_prices.json"
os.makedirs("data", exist_ok=True)

# Rotate between headers to avoid bot detection
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
]

import random

def _get_headers():
    return random.choice(HEADERS_LIST)


# -- URL content extraction ---------------------------------------------------

def fetch_url_text(url: str, max_chars: int = 6000) -> tuple[str, str]:
    try:
        session = requests.Session()
        session.headers.update(_get_headers())
        r = session.get(url, timeout=15, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else url
        main  = soup.find("article") or soup.find("main") or soup.find("body")
        text  = main.get_text(separator="\n", strip=True) if main else ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text  = "\n".join(lines)
        return title, text[:max_chars]

    except requests.exceptions.ConnectionError:
        return "", "Error: Could not reach the URL."
    except requests.exceptions.Timeout:
        return "", "Error: URL timed out."
    except requests.exceptions.HTTPError as e:
        return "", f"Error: HTTP {e.response.status_code} from URL."
    except Exception as e:
        return "", f"Error fetching URL: {e}"


def summarize_url(url: str, generate_llm_fn=None, model_type: str = "api") -> str:
    title, content = fetch_url_text(url)
    if content.startswith("Error:"):
        return content
    if not content.strip():
        return "Error: Could not extract readable content from that URL."
    if generate_llm_fn is None:
        return f"Title: {title}\n\n{content[:1000]}..."

    prompt = (
        f"Summarize the following article in clear bullet points.\n"
        f"Cover: main topic, key points, any conclusions.\n"
        f"Keep it under 200 words.\n\n"
        f"Title: {title}\n\nContent:\n{content}"
    )
    summary = generate_llm_fn(prompt, model_type)
    return f"Summary of: {title}\nURL: {url}\n\n{summary}"


# -- Price extraction ---------------------------------------------------------

AMAZON_SELECTORS = [
    {"id": "priceblock_ourprice"},
    {"id": "priceblock_dealprice"},
    {"id": "priceblock_saleprice"},
    {"class": "a-price-whole"},
    {"id": "price_inside_buybox"},
    {"id": "newBuyBoxPrice"},
    {"class": "priceToPay"},
]

FLIPKART_SELECTORS = [
    {"class": "Nx9bqj CxhGGd"},
    {"class": "_30jeq3 _16Jk6d"},
    {"class": "_25b18c"},
]

GENERIC_SELECTORS = [
    {"class": "price"},
    {"itemprop": "price"},
    {"class": "product-price"},
    {"class": "offer-price"},
]


def _extract_price_from_soup(soup: BeautifulSoup, url: str) -> str | None:
    selectors = []
    if "amazon" in url:
        selectors = AMAZON_SELECTORS + GENERIC_SELECTORS
    elif "flipkart" in url:
        selectors = FLIPKART_SELECTORS + GENERIC_SELECTORS
    else:
        selectors = GENERIC_SELECTORS

    for selector in selectors:
        el = soup.find(attrs=selector)
        if el:
            text = el.get_text(strip=True)
            # Clean — keep only digits, commas, dots
            clean = re.sub(r"[^\d,.]", "", text).strip()
            if clean and len(clean) >= 2:
                return clean

    # Try meta tags
    for meta_prop in ["product:price:amount", "og:price:amount"]:
        meta = soup.find("meta", {"property": meta_prop})
        if meta and meta.get("content"):
            return meta["content"]

    # Try JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json as _json
            data = _json.loads(script.string or "")
            if isinstance(data, dict):
                offers = data.get("offers", {})
                if isinstance(offers, dict):
                    price = offers.get("price")
                    if price:
                        return str(price)
        except Exception:
            pass

    return None


def _fetch_page(url: str) -> BeautifulSoup | None:
    try:
        session = requests.Session()
        # Add cookies to look more like a real browser
        session.headers.update(_get_headers())
        if "amazon" in url:
            session.headers["Referer"] = "https://www.google.com"
        time.sleep(random.uniform(0.5, 1.5))  # small delay
        r = session.get(url, timeout=15, allow_redirects=True)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None


# -- Price storage ------------------------------------------------------------

def _load_tracked() -> dict:
    try:
        if os.path.exists(PRICE_TRACK_FILE):
            with open(PRICE_TRACK_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_tracked(data: dict):
    with open(PRICE_TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -- Track price --------------------------------------------------------------

def track_price(url: str, item_name: str = "") -> str:
    soup = _fetch_page(url)
    if soup is None:
        return (
            "Error: Could not fetch the product page.\n"
            "Amazon may be blocking the request. Try again in a few seconds."
        )

    price_str = _extract_price_from_soup(soup, url)

    title = soup.title.string.strip() if soup.title else item_name or url
    name  = item_name or title[:60]

    if not price_str:
        # Still save the URL for future tracking even if price not found now
        tracked   = _load_tracked()
        entry_key = url[:100]
        history   = tracked.get(entry_key, {}).get("history", [])
        tracked[entry_key] = {
            "name":    name,
            "url":     url,
            "history": history,
        }
        _save_tracked(tracked)
        return (
            f"Tracking started for: {name}\n"
            f"Current price: Could not extract (Amazon may require login)\n"
            f"URL saved. Will check for drops on next price check.\n"
            f"Tip: Use 'show tracked prices' to see all tracked items."
        )

    # Save to history
    tracked   = _load_tracked()
    entry_key = url[:100]
    history   = tracked.get(entry_key, {}).get("history", [])
    history.append({
        "price": price_str,
        "date":  datetime.now().isoformat(),
    })

    tracked[entry_key] = {
        "name":    name,
        "url":     url,
        "history": history[-30:],
    }
    _save_tracked(tracked)

    # Check for price drop
    if len(history) >= 2:
        prev = history[-2]["price"]
        curr = history[-1]["price"]
        try:
            prev_f = float(prev.replace(",", ""))
            curr_f = float(curr.replace(",", ""))
            if curr_f < prev_f:
                diff = prev_f - curr_f
                pct  = (diff / prev_f) * 100
                return (
                    f"Price DROP detected for: {name}\n"
                    f"Previous : {prev}\n"
                    f"Current  : {curr}\n"
                    f"You save : {diff:.0f} ({pct:.1f}% off)\n"
                    f"Buy now  : {url}"
                )
        except ValueError:
            pass

    return (
        f"Tracking: {name}\n"
        f"Current price: {price_str}\n"
        f"Checks so far: {len(history)}\n"
        f"I will notify you if the price drops.\n"
        f"Say 'show tracked prices' to see all tracked items."
    )


def show_tracked_prices() -> str:
    tracked = _load_tracked()
    if not tracked:
        return "No products being tracked. Say 'track price <url>' to start."

    lines = [f"Tracked products ({len(tracked)}):\n"]
    for item in tracked.values():
        history = item.get("history", [])
        if not history:
            lines.append(f"- {item['name']}\n  Price: not yet fetched")
            continue
        latest = history[-1]
        prev   = history[-2]["price"] if len(history) >= 2 else None
        change = ""
        if prev:
            try:
                p = float(prev.replace(",", ""))
                c = float(latest["price"].replace(",", ""))
                if c < p:
                    change = f" (dropped from {prev})"
                elif c > p:
                    change = f" (up from {prev})"
            except ValueError:
                pass
        lines.append(
            f"- {item['name']}\n"
            f"  Price: {latest['price']}{change}\n"
            f"  Checked: {latest['date'][:10]}"
        )
    return "\n".join(lines)