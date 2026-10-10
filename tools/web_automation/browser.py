# tools/web_automation/browser.py
from core.logger import get_logger

logger = get_logger(__name__)


class Browser:
    def __init__(self):
        # Optional dependency (requirements-extras.txt): import only when a browser is opened.
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise RuntimeError(
                "Browser automation needs Playwright: pip install -r requirements-extras.txt "
                "&& playwright install chromium"
            ) from e

        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        self.page = self.browser.new_page()

    def open(self, url):
        logger.info(f"Opening {url}")
        self.page.goto(url, timeout=60000)

    def close(self):
        self.browser.close()
        self.p.stop()
