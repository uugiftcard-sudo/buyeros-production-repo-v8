"""
eBay seller & product scraper — search and seller profiles.

Supports both the eBay Browse API (preferred) and HTML fallback.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests

from src.models.ebay import ItemResult, SellerResult
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)

_API_BASE = "https://api.ebay.com/buy/browse/v1"
_HTML_BASE = "https://www.ebay.com"


class EbayScraper(BaseScraper[ItemResult]):
    """
    eBay product and seller scraper.

    Example:
        scraper = EbayScraper()
        items = scraper.search_items("iphone 15 pro")
        seller = scraper.fetch_seller("johndoe_uk")
    """

    name = "ebay"

    def __init__(self, delay: float = 2.0) -> None:
        super().__init__(delay=delay)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def scrape_item(self, url: str) -> ItemResult | None:
        """Stub — use search_items() instead."""
        return None

    # ── Product search ─────────────────────────────────────────

    def search_items(
        self,
        keyword: str,
        category: str = "",
        condition: str = "",
        max_price: str = "",
        min_price: str = "",
        sort: str = "best_match",
        limit: int = 50,
    ) -> list[ItemResult]:
        """
        Search eBay products by keyword.

        Tries the Browse API first, falls back to HTML scraping.
        """
        results = self._search_via_api(keyword, category, condition, max_price, min_price, sort, limit)
        if not results:
            _LOG.info("[eBay] API returned no results, trying HTML fallback")
            results = self._search_via_html(keyword, limit)
        return results

    def _search_via_api(
        self,
        keyword: str,
        category: str,
        condition: str,
        max_price: str,
        min_price: str,
        sort: str,
        limit: int,
    ) -> list[ItemResult]:
        """Search via eBay Browse API."""
        url = f"{_API_BASE}/item_summary/search"
        params: dict[str, Any] = {
            "q": keyword,
            "limit": min(limit, 100),
            "sort": sort,
        }
        if category:
            params["category_ids"] = category
        if max_price:
            params["max_price"] = max_price
        if min_price:
            params["min_price"] = min_price

        headers = {
            "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=,affiliateReferenceId=,contextualLocation=,usageType=SEARCH",
            "Accept": "application/json",
        }

        results: list[ItemResult] = []
        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code != 200:
                return results

            data = resp.json()
            items = data.get("itemSummaries", [])

            for item in items:
                r = ItemResult()
                r.search_keyword = keyword
                r.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                r.item_id = item.get("itemId", "")
                r.title = item.get("title", "")
                price = item.get("price", {})
                r.price = f"{price.get('value', '')} {price.get('currency', 'USD')}"
                r.currency = price.get("currency", "USD")
                r.condition = item.get("condition", "")
                r.listing_type = item.get("listingType", "")
                seller = item.get("seller", {})
                r.seller_id = seller.get("username", "")
                r.seller_rating = str(seller.get("feedbackScore", ""))
                r.location = item.get("location", "")
                cats = item.get("categories", [])
                r.category = cats[0].get("categoryName", "") if cats else ""
                img = item.get("image", {})
                r.image_url = img.get("imageUrl", "") if isinstance(img, dict) else ""
                r.detail_url = item.get("itemWebUrl", "")
                results.append(r)

            _LOG.info(f"[eBay API] Found {len(results)} items for '{keyword}'")

        except requests.RequestException as e:
            _LOG.error(f"[eBay API] Request failed: {e}")

        return results

    def _search_via_html(self, keyword: str, limit: int) -> list[ItemResult]:
        """HTML fallback when API is unavailable."""
        search_url = f"{_HTML_BASE}/sch/i.html?_nkw={requests.utils.quote(keyword)}&_ipg=60"
        results: list[ItemResult] = []

        try:
            resp = self.session.get(search_url, timeout=20)
            resp.raise_for_status()
            soup = make_soup(resp.text)
            items = soup.select("[class*='s-item']")

            for item in items[:limit]:
                r = ItemResult()
                r.search_keyword = keyword
                r.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

                title_tag = item.select_one("[class*='s-item__title']")
                if title_tag:
                    r.title = title_tag.get_text(strip=True)

                price_tag = item.select_one("[class*='s-item__price']")
                if price_tag:
                    r.price = price_tag.get_text(strip=True)

                cond_tag = item.select_one("[class*='s-item__subtitle']")
                if cond_tag:
                    r.condition = cond_tag.get_text(strip=True)

                link_tag = item.select_one("a.s-item__link")
                if link_tag and link_tag.get("href"):
                    href = link_tag.get("href", "")
                    r.detail_url = href
                    m = re.search(r"/(\d+)\?", href)
                    if m:
                        r.item_id = m.group(1)

                seller_tag = item.select_one("[class*='s-item__seller']")
                if seller_tag:
                    r.seller_id = seller_tag.get_text(strip=True).replace("Seller:", "").strip()

                results.append(r)
                time.sleep(self.delay)

            _LOG.info(f"[eBay HTML] Found {len(results)} items")

        except requests.RequestException as e:
            _LOG.error(f"[eBay HTML] Request failed: {e}")

        return results

    # ── Seller profile ──────────────────────────────────────────

    def fetch_seller(self, seller_id: str) -> SellerResult | None:
        """Fetch seller public profile."""
        url = f"{_HTML_BASE}/usr/{seller_id}"
        s = SellerResult()
        s.seller_id = seller_id
        s.detail_url = url

        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            soup = make_soup(resp.text)

            name_tag = soup.select_one("[class*='user-name'], [class*='member-name'] h1")
            if name_tag:
                s.seller_name = name_tag.get_text(strip=True)

            score_tag = soup.select_one("[class*='feedback-score']")
            if score_tag:
                s.feedback_score = score_tag.get_text(strip=True)

            pct_tag = soup.select_one("[class*='feedback-percentage']")
            if pct_tag:
                s.feedback_percent = pct_tag.get_text(strip=True)

            since_tag = soup.select_one("[class*='member-since']")
            if since_tag:
                s.member_since = since_tag.get_text(strip=True)

            loc_tag = soup.select_one("[class*='user-location']")
            if loc_tag:
                s.location = loc_tag.get_text(strip=True)

            s.top_rated = bool(soup.select_one("[class*='top-rated']"))

            _LOG.info(f"[eBay] Seller {s.seller_id}: score={s.feedback_score}, location={s.location}")
            return s

        except requests.RequestException as e:
            _LOG.error(f"[eBay] Seller fetch failed: {e}")
            return None

    def fetch_sellers(self, seller_ids: list[str]) -> list[SellerResult]:
        """Fetch multiple seller profiles sequentially."""
        results: list[SellerResult] = []
        for sid in seller_ids:
            self._wait()
            s = self.fetch_seller(sid)
            if s:
                results.append(s)
        return results
