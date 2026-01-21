import webbrowser
import urllib.parse


def open_youtube():
    webbrowser.open("https://www.youtube.com")
    return "YouTube opened in browser."


def search_youtube(query: str):
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}"
    webbrowser.open(url)
    return f"YouTube search opened for: {query}"
    