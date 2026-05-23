"""
UK Supermarket Price Scraper — John Lewis, Tesco, M&S.

Price comparison across multiple UK retailers with optional CSV/JSON export.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests

from src.models.supermarket import SupermarketResult
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)


class SupermarketScraper(BaseScraper[SupermarketResult]):
    """
    UK supermarket price scraper — John Lewis, Tesco, M&S.

    Example:
        scraper = SupermarketScraper()
        results = scraper.compare_price("whole milk")
        results = scraper.search_john_lewis("dyson vacuum")
    """

    name = "supermarket"

    def __init__(self, delay: float = 2.0) -> None:
        super().__init__(delay=delay)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def scrape_item(self, url: str) -> SupermarketResult | None:
        raise NotImplementedError("Use retailer-specific search methods")

    @staticmethod
    def _price(text: str) -> str:
        if not text:
            return ""
        m = re.search(r"[\$£]?\s*([\d,]+\.?\d*)", text)
        return m.group(0).strip() if m else text.strip()

    # ── John Lewis ──────────────────────────────────────────────

    def search_john_lewis(self, keyword: str, limit: int = 30) -> list[SupermarketResult]:
        """Search John Lewis products."""
        results: list[SupermarketResult] = []
        url = "https://www.johnlewis.com/search"
        params = {"search-term": keyword, "pageSize": limit}

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            soup = make_soup(resp.text)

            # JSON script extraction
            for script in soup.find_all("script"):
                text = script.string or ""
                if '"products"' not in text and '"items"' not in text:
                    continue

                json_matches = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text)
                for m in json_matches[:limit]:
                    try:
                        obj = __import__("json").loads(m)
                        if not (obj.get("name") or obj.get("title") or obj.get("productName")):
                            continue
                        p = SupermarketResult()
                        p.retailer = "John Lewis"
                        p.search_keyword = keyword
                        p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                        p.name = obj.get("name") or obj.get("title") or obj.get("productName", "")
                        p.brand = obj.get("brand", "")
                        price_info = obj.get("price", {})
                        if isinstance(price_info, dict):
                            p.price = f"£{price_info.get('now', '')}"
                            p.original_price = f"£{price_info.get('was', '')}"
                        else:
                            p.price = str(price_info)
                        p.unit_price = obj.get("unitPrice", "")
                        p.promotion = obj.get("promotion", obj.get("label", ""))
                        p.rating = str(obj.get("rating", ""))
                        p.review_count = str(obj.get("reviewCount", ""))
                        p.availability = obj.get("availability", "")
                        p.image_url = obj.get("image", obj.get("imageUrl", ""))
                        pu = obj.get("url", obj.get("productUrl", ""))
                        p.product_url = "https://www.johnlewis.com" + pu if pu else ""
                        results.append(p)
                        if len(results) >= limit:
                            break
                    except Exception:  # noqa: BLE001
                        pass
                if results:
                    break

            # HTML fallback
            if not results:
                for card in soup.select("[class*='product-card'], [class*='product-item']")[:limit]:
                    p = SupermarketResult()
                    p.retailer = "John Lewis"
                    p.search_keyword = keyword
                    p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                    name_tag = card.select_one("[class*='product-name'], h3, h4, a")
                    if name_tag:
                        p.name = name_tag.get_text(strip=True)
                    price_tag = card.select_one("[class*='price'], [class*='now']")
                    if price_tag:
                        p.price = price_tag.get_text(strip=True)
                    promo_tag = card.select_one("[class*='promo'], [class*='sale']")
                    if promo_tag:
                        p.promotion = promo_tag.get_text(strip=True)
                    link_tag = card.select_one("a[href*='/p']")
                    if link_tag and link_tag.get("href"):
                        p.product_url = "https://www.johnlewis.com" + link_tag["href"]
                    if p.name:
                        results.append(p)

            _LOG.info(f"[John Lewis] Found {len(results)} items for '{keyword}'")

        except requests.RequestException as e:
            _LOG.error(f"[John Lewis] Request failed: {e}")

        return results

    # ── Tesco ──────────────────────────────────────────────────

    def search_tesco(self, keyword: str, limit: int = 30) -> list[SupermarketResult]:
        """Search Tesco grocery products."""
        results: list[SupermarketResult] = []
        search_url = (
            f"https://www.tesco.com/groceries/en-GB/search?q={requests.utils.quote(keyword)}"
        )

        try:
            resp = self.session.get(search_url, timeout=15)
            resp.raise_for_status()
            soup = make_soup(resp.text)

            # JSON-LD extraction
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = __import__("json").loads(script.string or "")
                    if isinstance(data, list):
                        for obj in data:
                            if obj.get("@type") == "Product":
                                p = self._parse_tesco_product(obj, keyword)
                                if p:
                                    results.append(p)
                    elif isinstance(data, dict) and data.get("@type") == "Product":
                        p = self._parse_tesco_product(data, keyword)
                        if p:
                            results.append(p)
                except Exception:  # noqa: BLE001
                    pass
                if len(results) >= limit:
                    break

            # HTML fallback
            if not results:
                for item in soup.select("[class*='product-tile']")[:limit]:
                    p = SupermarketResult()
                    p.retailer = "Tesco"
                    p.search_keyword = keyword
                    p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                    name_tag = item.select_one("[class*='product-name'], h3, h4")
                    if name_tag:
                        p.name = name_tag.get_text(strip=True)
                    price_tag = item.select_one("[class*='price']")
                    if price_tag:
                        p.price = price_tag.get_text(strip=True)
                    promo_tag = item.select_one("[class*='promotion'], [class*='deal']")
                    if promo_tag:
                        p.promotion = promo_tag.get_text(strip=True)
                    if p.name:
                        results.append(p)

            _LOG.info(f"[Tesco] Found {len(results)} items for '{keyword}'")

        except requests.RequestException as e:
            _LOG.error(f"[Tesco] Request failed: {e}")

        return results

    def _parse_tesco_product(self, obj: dict[str, Any], keyword: str) -> SupermarketResult | None:
        p = SupermarketResult()
        p.retailer = "Tesco"
        p.search_keyword = keyword
        p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
        p.name = obj.get("name", "")
        p.brand = obj.get("brand", "")
        offers = obj.get("offers", {})
        if isinstance(offers, dict):
            p.price = str(offers.get("price", ""))
            p.currency = str(offers.get("priceCurrency", "GBP"))
        elif isinstance(offers, list) and offers:
            p.price = str(offers[0].get("price", ""))
        p.unit_price = str(obj.get("unitPriceText", ""))
        rating = obj.get("aggregateRating", {})
        if isinstance(rating, dict):
            p.rating = str(rating.get("ratingValue", ""))
            p.review_count = str(rating.get("reviewCount", ""))
        img = obj.get("image", [])
        p.image_url = img[0] if isinstance(img, list) else str(img)
        return p if p.name else None

    # ── M&S ────────────────────────────────────────────────────

    def search_marks_and_spencer(self, keyword: str, limit: int = 30) -> list[SupermarketResult]:
        """Search M&S products."""
        results: list[SupermarketResult] = []
        search_url = f"https://www.marksandspencer.com/search?q={requests.utils.quote(keyword)}"

        try:
            resp = self.session.get(search_url, timeout=15)
            resp.raise_for_status()
            soup = make_soup(resp.text)

            for item in soup.select("[class*='product'], [class*='item'], [data-product]")[:limit]:
                p = SupermarketResult()
                p.retailer = "M&S"
                p.search_keyword = keyword
                p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                name_tag = item.select_one("[class*='name'], [class*='title'], h3, h4")
                if name_tag:
                    p.name = name_tag.get_text(strip=True)
                price_tag = item.select_one("[class*='price'], [class*='now']")
                if price_tag:
                    p.price = price_tag.get_text(strip=True)
                link_tag = item.select_one("a[href*='/p/']")
                if link_tag and link_tag.get("href"):
                    p.product_url = "https://www.marksandspencer.com" + link_tag["href"]
                if p.name:
                    results.append(p)

            _LOG.info(f"[M&S] Found {len(results)} items for '{keyword}'")

        except requests.RequestException as e:
            _LOG.error(f"[M&S] Request failed: {e}")

        return results

    # ── Price comparison ────────────────────────────────────────

    def compare_price(self, keyword: str, delay: float | None = None) -> list[SupermarketResult]:
        """
        Search all supported retailers for a keyword.

        Adds inter-retailer delay automatically.
        """
        results: list[SupermarketResult] = []
        results += self.search_john_lewis(keyword)
        time.sleep(delay or self.delay)
        results += self.search_tesco(keyword)
        time.sleep(delay or self.delay)
        results += self.search_marks_and_spencer(keyword)
        return results
