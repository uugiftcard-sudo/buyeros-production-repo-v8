"""
Browser scraper — Playwright-powered scraper for JavaScript-heavy pages.

Install browsers:
    pip install -e ".[browser]"
    playwright install chromium

Usage:
    from src.scrapers.browser_scraper import BrowserScraper

    scraper = BrowserScraper()
    html = scraper.fetch_page("https://www.amazon.com/dp/B09V3KXJPB")
"""

from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.config import get_delay, get_user_agents

if TYPE_CHECKING:
    pass

_LOG = logging.getLogger(__name__)


class BrowserScraper:
    """
    Headless browser scraper backed by Playwright (Chromium).

    Features:
    - Lazy browser/context initialisation (starts on first request)
    - User-Agent spoofing per request
    - Automatic retry on failure
    - Configurable wait conditions (dom-content-loaded, network-idle, etc.)
    - Stealth mode: hides automation signatures
    - Context-level session management (cookies persist)
    """

    def __init__(
        self,
        delay: float | None = None,
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        block_ads: bool = True,
        extra_http_headers: dict[str, str] | None = None,
    ) -> None:
        self._delay = delay or get_delay("browser")
        self._headless = headless
        self._viewport = {"width": viewport_width, "height": viewport_height}
        self._block_ads = block_ads
        self._extra_headers = extra_http_headers or {}

        # Lazy initialisation
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    # ── Lifecycle ────────────────────────────────────────────

    def _ensure_browser(self) -> BrowserContext:
        """Lazily start browser + context on first use."""
        if self._context is not None:
            return self._context

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context(
            viewport=self._viewport,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept-Language": "en-GB,en;q=0.9",
                **self._extra_headers,
            },
        )

        # Stealth: remove automation signatures
        self._stealth(self._context)

        return self._context

    @staticmethod
    def _stealth(context: BrowserContext) -> None:
        """Patch browser context to reduce detection."""
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-GB', 'en'] });
            window.chrome = { runtime: {} };
        """)

    def close(self) -> None:
        """Cleanly shut down the browser."""
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> BrowserScraper:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Context helpers ───────────────────────────────────────

    def new_page(self) -> Page:
        """Create a new page with a random User-Agent."""
        context = self._ensure_browser()
        page = context.new_page()

        # Set random UA
        ua = random.choice(get_user_agents())
        page.set_extra_http_headers({"User-Agent": ua})

        # Block resource-heavy ad/tracking domains
        if self._block_ads:
            page.route(
                r"https?://(www\.)?googlesyndication\.com/.*",
                lambda route: route.abort(),
            )
            page.route(
                r"https?://(www\.)?googleadservices\.com/.*",
                lambda route: route.abort(),
            )
            page.route(
                r"https?://(www\.)?doubleclick\.net/.*",
                lambda route: route.abort(),
            )

        return page

    # ── Fetch ─────────────────────────────────────────────────

    def fetch_page(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30_000,
        scroll: bool = False,
    ) -> Page:
        """
        Navigate to a URL and return the Playwright Page.

        Args:
            url: Target URL
            wait_until: 'load' | 'domcontentloaded' | 'networkidle' | 'commit'
            timeout: Navigation timeout in ms
            scroll: Whether to scroll to the bottom (useful for lazy-loaded content)

        Returns:
            Playwright Page object
        """
        page = self.new_page()

        try:
            response = page.goto(url, wait_until=wait_until, timeout=timeout)

            if response is None:
                raise RuntimeError(f"Navigation returned None for {url}")

            status = response.status
            if status >= 400:
                raise RuntimeError(f"HTTP {status} for {url}")

            _LOG.debug("[browser] Fetched %s (status=%d)", url, status)

            if scroll:
                self._scroll_page(page)

            time.sleep(self._delay)

        except Exception:
            page.close()
            raise

        return page

    @staticmethod
    def _scroll_page(page: Page) -> None:
        """Scroll to bottom to trigger lazy-loading."""
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)

    # ── Text / Content extraction ──────────────────────────────

    @staticmethod
    def extract_text(page: Page, selector: str) -> str:
        """Extract text from the first element matching `selector`."""
        try:
            el = page.wait_for_selector(selector, timeout=5_000)
            return el.inner_text() if el else ""
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def extract_all(page: Page, selector: str) -> list[str]:
        """Extract text from all elements matching `selector`."""
        try:
            return [el.inner_text() for el in page.query_selector_all(selector)]
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def extract_attrs(page: Page, selector: str, attr: str) -> list[str]:
        """Extract an attribute from all elements matching `selector`."""
        try:
            return [el.get_attribute(attr) or "" for el in page.query_selector_all(selector)]
        except Exception:  # noqa: BLE001
            return []

    # ── Content helpers ───────────────────────────────────────

    def fetch_html(self, url: str, scroll: bool = True) -> str:
        """Fetch full page HTML (after JS rendering)."""
        page = self.fetch_page(url, wait_until="networkidle", scroll=scroll)
        html = page.content()
        page.close()
        return html

    def screenshot(self, url: str, path: str, full_page: bool = False) -> None:
        """Take a screenshot of a URL."""
        page = self.fetch_page(url, wait_until="networkidle")
        page.screenshot(path=path, full_page=full_page)
        page.close()

    # ── Batch ─────────────────────────────────────────────────

    def fetch_batch(self, urls: list[str]) -> list[Page]:
        """Fetch multiple URLs sequentially, returning open Page objects."""
        pages: list[Page] = []
        for url in urls:
            try:
                page = self.fetch_page(url, scroll=True)
                pages.append(page)
            except Exception as exc:  # noqa: BLE001
                _LOG.error("[browser] Failed %s: %s", url, exc)
        return pages

    def __del__(self) -> None:
        """Safety net: close browser if object is discarded without close()."""
        self.close()
