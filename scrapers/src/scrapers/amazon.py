"""
Amazon product price monitor — search and ASIN detail.

Scrapes amazon.com / amazon.co.uk for product listings.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests

from src.models.amazon import ProductResult
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)

_AMAZON_DOMAINS: dict[str, str] = {
    "com": "https://www.amazon.com",
    "co.uk": "https://www.amazon.co.uk",
}


class AmazonScraper(BaseScraper[ProductResult]):
    """
    Amazon product scraper supporting search and ASIN detail.

    Example:
        scraper = AmazonScraper()
        products = scraper.search_by_keyword("wireless headphones", pages=2)
        detail = scraper.fetch_product_detail("B09V3KXJPB")
    """

    name = "amazon"

    def __init__(
        self,
        domain: str = "com",
        delay: float = 3.0,
        max_retries: int | None = None,
    ) -> None:
        super().__init__(delay=delay, max_retries=max_retries)
        self.domain = domain
        self.base_url = _AMAZON_DOMAINS.get(domain, _AMAZON_DOMAINS["com"])

    def scrape_item(self, url: str) -> ProductResult | None:
        """Stub — not used directly. Use fetch_product_detail() instead."""
        asin = self._extract_asin(url)
        if asin:
            return self.fetch_product_detail(asin)
        return None

    @staticmethod
    def _extract_asin(url_or_text: str) -> str:
        """Pull ASIN from URL or return input if it looks like an ASIN."""
        m = re.search(r"/(dp|gp/product)/([A-Z0-9]{10})", url_or_text)
        if m:
            return m.group(2)
        if re.match(r"^[A-Z0-9]{10}$", url_or_text.strip()):
            return url_or_text.strip()
        return ""

    @staticmethod
    def _price(text: str) -> str:
        if not text:
            return ""
        m = re.search(r"[\$£]?\s*([\d,]+\.?\d*)", text)
        return m.group(0).strip() if m else text.strip()

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        base = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        if extra:
            base.update(extra)
        return base

    def fetch_search_page(self, keyword: str, page: int = 1) -> str | None:
        """Fetch raw HTML for a search results page."""
        page_param = f"&page={page}" if page > 1 else ""
        url = f"{self.base_url}/s?k={requests.utils.quote(keyword)}{page_param}"
        resp = self._get(url)
        return resp.text if resp else None

    def parse_search_results(self, html: str, keyword: str) -> list[ProductResult]:
        """Parse search results HTML into ProductResult list."""
        soup = make_soup(html)
        results: list[ProductResult] = []

        items = soup.select("[data-component-type='s-search-result']")

        for item in items:
            p = ProductResult()
            p.search_keyword = keyword
            p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

            # ASIN
            p.asin = item.get("data-asin", "") or re.sub(r"result_", "", item.get("id", ""))

            # Title
            title_tag = item.select_one("h2 a span, a.a-color-base.a-text-normal span")
            if title_tag:
                p.title = title_tag.get_text(strip=True)

            # Price
            price_tag = item.select_one(
                "[class*='price'] span.a-offscreen, .a-price .a-offscreen"
            )
            if price_tag:
                p.price = price_tag.get_text(strip=True)

            # Original price
            orig_tag = item.select_one("[class*='strike'], [class*='list']")
            if orig_tag:
                p.original_price = orig_tag.get_text(strip=True)

            # Rating
            rating_tag = item.select_one("[class*='a-icon-star'] span")
            if rating_tag:
                p.rating = rating_tag.get_text(strip=True)

            # Review count
            review_tag = item.select_one("span.a-size-base.s-underline-text")
            if review_tag:
                p.review_count = review_tag.get_text(strip=True)

            # Category
            cat_tag = item.select_one("[class*='category']")
            if cat_tag:
                p.category = cat_tag.get_text(strip=True)

            # Badges
            p.amazon_choice = "Yes" if item.select_one("[class*='amazon-choice']") else "No"
            p.best_seller_badge = "Yes" if item.select_one("[class*='best-seller']") else "No"

            # URL
            link_tag = item.select_one("h2 a, a.a-link-normal")
            if link_tag and link_tag.get("href"):
                href = link_tag.get("href", "")
                base = self.base_url if "com" in self.domain else _AMAZON_DOMAINS["co.uk"]
                p.detail_url = base + href.split("?")[0]

            if p.asin and p.title:
                results.append(p)

        return results

    def fetch_product_detail(self, asin: str) -> ProductResult | None:
        """Fetch detailed product information for a single ASIN."""
        url = f"{self.base_url}/dp/{asin}"
        p = ProductResult()
        p.asin = asin
        p.detail_url = url
        p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

        resp = self._get(url)
        if resp is None:
            return None

        soup = make_soup(resp.text)

        # Title
        title_tag = soup.select_one("#productTitle, #title")
        if title_tag:
            p.title = title_tag.get_text(strip=True)

        # Price
        price_tag = soup.select_one(".a-price .a-offscreen, #priceblock_ourprice")
        if price_tag:
            p.price = price_tag.get_text(strip=True)

        # Rating
        rating_tag = soup.select_one("#acrPopover .a-icon-alt")
        if rating_tag:
            p.rating = rating_tag.get_text(strip=True)

        # Review count
        review_tag = soup.select_one("#acrCustomerReviewText")
        if review_tag:
            p.review_count = review_tag.get_text(strip=True)

        # Category / rank
        rank_tags = soup.select("#SalesRank .a-text-medium, #detailBulletsWrapper_feature_div li")
        rank_text = " | ".join(t.get_text(strip=True) for t in rank_tags[:3])
        if rank_text:
            p.rank = rank_text

        # Brand
        brand_tag = soup.select_one("#bylineInfo, [class*='brand']")
        if brand_tag:
            p.brand = brand_tag.get_text(strip=True)

        # Availability
        avail_tag = soup.select_one("#availability span")
        if avail_tag:
            p.availability = avail_tag.get_text(strip=True)

        _LOG.info(f"[Amazon] Fetched detail: {p.title[:60]}")
        return p

    def search_by_keyword(
        self,
        keyword: str,
        pages: int = 2,
        delay: float | None = None,
    ) -> list[ProductResult]:
        """
        Search Amazon by keyword across multiple pages.

        Args:
            keyword: Search term
            pages: Number of result pages to fetch
            delay: Delay between pages (overrides instance default)
        """
        all_results: list[ProductResult] = []
        delay = delay if delay is not None else self.delay

        for page in range(1, pages + 1):
            _LOG.info(f"[Amazon] Searching '{keyword}' page {page}/{pages}")
            html = self.fetch_search_page(keyword, page)
            if html:
                results = self.parse_search_results(html, keyword)
                all_results.extend(results)
                _LOG.info(f"[Amazon] Page {page}: found {len(results)} items")
            time.sleep(delay)

        return all_results

    def scrape_batch(self, asins: list[str]) -> list[ProductResult]:
        """Scrape multiple ASINs sequentially."""
        self.reset()
        results: list[ProductResult] = []
        for asin in asins:
            self._wait()
            p = self.fetch_product_detail(asin)
            if p:
                results.append(p)
        return results
