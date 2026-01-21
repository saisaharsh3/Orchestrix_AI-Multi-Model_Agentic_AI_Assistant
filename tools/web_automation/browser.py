# tools/web_automation/browser.py
from playwright.sync_api import sync_playwright

class Browser:
    def __init__(self):
        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        self.page = self.browser.new_page()

    def open(self, url):
        print(f" Opening {url}")
        self.page.goto(url, timeout=60000)

    def close(self):
        self.browser.close()
        self.p.stop()
