"""
Enhanced Amazon scraper using Playwright — bypasses anti-bot detection.

Requires:
    pip install -e ".[browser]"
    playwright install chromium

Usage:
    scrapers amazon --keyword laptop --browser
    scrapers amazon --asin B09V3KXJPB --browser
"""

from __future__ import annotations

import logging
import re
import time

from playwright.sync_api import Page

from src.models.amazon import AmazonProductResult
from src.scrapers.browser_scraper import BrowserScraper
from src.utils.html import extract_price

_LOG = logging.getLogger(__name__)


class AmazonBrowserScraper:
    """
    Headless browser Amazon scraper — renders JavaScript pages.

    Works for:
    - Product detail pages (/dp/ASIN)
    - Search results pages (/s?k=...)
    - Best seller pages (/gp/bestsellers/...)
    """

    BASE_URL = "https://www.amazon.com"
    SEARCH_URL = "https://www.amazon.com/s?k={keyword}&page={page}"

    def __init__(self, domain: str = "com", delay: float = 3.0) -> None:
        self.domain = domain
        self.delay = delay
        self.browser = BrowserScraper(delay=delay, headless=True)
        self.base_url = {
            "com": "https://www.amazon.com",
            "co.uk": "https://www.amazon.co.uk",
        }.get(domain, self.BASE_URL)

    def close(self) -> None:
        self.browser.close()

    # ── Search ────────────────────────────────────────────────

    def search(self, keyword: str, pages: int = 2) -> list[AmazonProductResult]:
        """Search Amazon for a keyword and return product results."""
        results: list[AmazonProductResult] = []

        for page_num in range(1, pages + 1):
            url = self.SEARCH_URL.format(keyword=keyword.replace(" ", "+"), page=page_num)
            _LOG.info("[amazon] Search page %d: %s", page_num, url)

            try:
                page = self.browser.fetch_page(url, wait_until="networkidle", scroll=True)
                items = self._parse_search_results(page, keyword)
                results.extend(items)
                _LOG.info("[amazon] Page %d: got %d results", page_num, len(items))
                page.close()
            except Exception as exc:  # noqa: BLE001
                _LOG.error("[amazon] Page %d failed: %s", page_num, exc)

            time.sleep(self.delay)

        return results

    def _parse_search_results(self, page: Page, keyword: str) -> list[AmazonProductResult]:
        """Parse Amazon search results page."""
        results: list[AmazonProductResult] = []

        # Try product cards (main grid layout)
        cards = page.query_selector_all(
            "[data-component-type='s-search-result'], "
            ".s-result-item[data-component-type='s-search-result'], "
            "div[cel_widget_id^='MAIN-SEARCH']"
        )

        if not cards:
            # Fallback: simpler selector
            cards = page.query_selector_all(".s-result-item")

        for card in cards:
            try:
                # ASIN
                asin = card.get_attribute("data-asin") or ""
                if not asin or len(asin) < 5:
                    continue

                # Product link
                link_el = card.query_selector("a.a-link-normal.s-no-outline")
                if not link_el:
                    link_el = card.query_selector("h2 a")
                product_url = self.base_url + link_el.get_attribute("href") if link_el else ""
                if "amazon.com" not in product_url:
                    product_url = link_el.get_attribute("href") or "" if link_el else ""

                # Name
                name_el = card.query_selector("h2 a span, .a-size-medium.a-color-base")
                name = name_el.inner_text().strip() if name_el else ""

                # Price
                price_el = card.query_selector(".a-price .a-offscreen, .a-price-whole")
                price = extract_price(price_el.inner_text()) if price_el else ""

                # Original price (crossed out)
                orig_el = card.query_selector(".a-text-price .a-offscreen, [class*='was']")
                original_price = extract_price(orig_el.inner_text()) if orig_el else ""

                # Rating
                rating_el = card.query_selector(
                    ".a-icon-star-small .a-icon-alt, [class*='rating'] span"
                )
                rating = rating_el.inner_text().strip().split()[0] if rating_el else ""

                # Review count
                reviews_el = card.query_selector(
                    ".a-size-small .a-link-normal, "
                    "[class*='rating'] [class*='small'], "
                    "span.a-size-base"
                )
                reviews = re.sub(r"[^\d]", "", reviews_el.inner_text()) if reviews_el else ""

                # Badge
                badge_el = card.query_selector(
                    ".a-badge-label .a-badge-text, [class*='badge'] span"
                )
                badge = badge_el.inner_text().strip() if badge_el else ""

                results.append(
                    AmazonProductResult(
                        asin=asin,
                        name=name,
                        price=price,
                        original_price=original_price,
                        rating=rating,
                        review_count=reviews,
                        search_keyword=keyword,
                        product_url=product_url,
                        badge=badge,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                _LOG.debug("[amazon] Card parse error: %s", exc)
                continue

        return results

    # ── ASIN detail ───────────────────────────────────────────

    def get_product(self, asin: str) -> AmazonProductResult | None:
        """Get full product details for a single ASIN."""
        url = f"{self.base_url}/dp/{asin}"
        _LOG.info("[amazon] Fetching ASIN: %s", asin)

        try:
            page = self.browser.fetch_page(url, wait_until="networkidle", scroll=True)
            result = self._parse_detail_page(page, asin)
            page.close()
            return result
        except Exception as exc:  # noqa: BLE001
            _LOG.error("[amazon] ASIN %s failed: %s", asin, exc)
            return None

    def _parse_detail_page(self, page: Page, asin: str) -> AmazonProductResult:
        """Parse Amazon product detail page."""
        # Product title
        title_el = page.query_selector("#productTitle")
        name = title_el.inner_text().strip() if title_el else ""

        # Price
        price_el = page.query_selector(
            "#priceblock_ourprice, "
            "#priceblock_dealprice, "
            ".a-price .a-offscreen, "
            "#corePrice_feature_div .a-offscreen"
        )
        price = extract_price(price_el.inner_text()) if price_el else ""

        # Rating
        rating_el = page.query_selector("#acrPopover .a-icon-alt, .a-icon-star")
        rating = rating_el.inner_text().strip().split()[0] if rating_el else ""

        # Reviews count
        reviews_el = page.query_selector("#acrCustomerReviewText")
        reviews = re.sub(r"[^\d]", "", reviews_el.inner_text()) if reviews_el else ""

        # Bullet points / description
        bullets = [
            el.inner_text().strip() for el in page.query_selector_all("#feature-bullets li span")
        ]
        description = " | ".join(b for b in bullets if b) if bullets else ""

        # Category
        cat_el = page.query_selector("#wayfinding-breadcrumbs_feature_div li span a")
        category = cat_el.inner_text().strip() if cat_el else ""

        # BSR (Best Sellers Rank)
        bsr_el = page.query_selector("#SalesRank, [id*='rank']")
        bsr = bsr_el.inner_text().strip() if bsr_el else ""

        return AmazonProductResult(
            asin=asin,
            name=name,
            price=price,
            rating=rating,
            review_count=reviews,
            category=category,
            description=description,
            best_sellers_rank=bsr,
            search_keyword="",
        )
