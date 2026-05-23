"""
Enhanced Tesco supermarket scraper using Playwright.

Requires:
    pip install -e ".[browser]"
    playwright install chromium

Usage:
    scrapers supermarket -c -k "whole milk" --browser
    scrapers supermarket -r tesco -k "chicken" --browser
"""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from src.models.supermarket import SupermarketResult
from src.scrapers.browser_scraper import BrowserScraper

_LOG = logging.getLogger(__name__)


class TescoBrowserScraper:
    """
    Headless browser Tesco scraper — renders JS-rendered product grids.

    Works for:
    - Grocery search: https://www.tesco.com/groceries/en-GB/search?q=...
    - Product detail pages
    """

    BASE_URL = "https://www.tesco.com/groceries/en-GB/search?q={keyword}"

    def __init__(self, delay: float = 2.0, headless: bool = True) -> None:
        self.delay = delay
        self.browser = BrowserScraper(delay=delay, headless=headless)

    def close(self) -> None:
        self.browser.close()

    def search(self, keyword: str, limit: int = 30) -> list[SupermarketResult]:
        """Search Tesco Groceries and return product results."""
        url = self.BASE_URL.format(keyword=keyword.replace(" ", "+"))
        _LOG.info("[tesco] Searching: %s", url)

        results: list[SupermarketResult] = []

        try:
            page = self.browser.fetch_page(url, wait_until="networkidle", scroll=True)

            # Wait for product grid to load
            try:
                page.wait_for_selector(
                    "[data-testid='product-tile'], .product-tile, [class*='product']",
                    timeout=10_000,
                )
            except Exception:  # noqa: BLE001
                _LOG.warning("[tesco] Product grid not found — page may require login")

            results = self._parse_search_results(page, keyword, limit)
            _LOG.info("[tesco] Got %d results for '%s'", len(results), keyword)

            page.close()

        except Exception as exc:  # noqa: BLE001
            _LOG.error("[tesco] Search failed: %s", exc)

        return results

    def _parse_search_results(
        self, page: Page, keyword: str, limit: int = 30
    ) -> list[SupermarketResult]:
        """Parse Tesco search results page."""
        results: list[SupermarketResult] = []

        # Try multiple selectors (Tesco changes these frequently)
        tiles = (
            page.query_selector_all("[data-testid='product-tile']")
            or page.query_selector_all(".product-tile")
            or page.query_selector_all("[class*='product-card']")
            or page.query_selector_all("li[data-auto-id]")
        )

        for tile in tiles:
            try:
                # Product name
                name_el = (
                    tile.query_selector("[data-testid='product-title']")
                    or tile.query_selector(".product-title")
                    or tile.query_selector("h3, h4")
                )
                name = name_el.inner_text().strip() if name_el else ""
                if not name:
                    continue

                # Price
                price_el = (
                    tile.query_selector("[data-testid='price']")
                    or tile.query_selector(".price")
                    or tile.query_selector("[class*='price']")
                )
                price = price_el.inner_text().strip() if price_el else ""

                # Clubcard price
                clubcard_el = (
                    tile.query_selector("[data-testid='clubcard-price']")
                    or tile.query_selector(".clubcard-price")
                    or tile.query_selector("[class*='clubcard']")
                )
                clubcard_price = clubcard_el.inner_text().strip() if clubcard_el else ""

                # Unit price (per kg / per litre)
                unit_el = (
                    tile.query_selector("[data-testid='price-subtext']")
                    or tile.query_selector(".unit-price")
                    or tile.query_selector("[class*='per-']")
                )
                unit_price = unit_el.inner_text().strip() if unit_el else ""

                # Link
                link_el = tile.query_selector("a[href*='/p/']")
                link = "https://www.tesco.com" + link_el.get_attribute("href") if link_el else ""

                # Image
                img_el = tile.query_selector("img[src], img[data-src]")
                img = (
                    img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""
                    if img_el
                    else ""
                )

                # Promotion
                promo_el = tile.query_selector("[class*='promotion'], [class*='deal']")
                promotion = promo_el.inner_text().strip() if promo_el else ""

                results.append(
                    SupermarketResult(
                        name=name,
                        price=price,
                        unit_price=unit_price,
                        promotion=promotion,
                        product_url=link,
                        image_url=img,
                        retailer="Tesco",
                        search_keyword=keyword,
                        clubcard_price=clubcard_price,
                    )
                )

            except Exception as exc:  # noqa: BLE001
                _LOG.debug("[tesco] Tile parse error: %s", exc)
                continue

        return results[:limit]

    def get_product(self, url: str) -> SupermarketResult | None:
        """Get product details from a Tesco product page URL."""
        _LOG.info("[tesco] Fetching: %s", url)

        try:
            page = self.browser.fetch_page(url, wait_until="networkidle", scroll=True)
            result = self._parse_detail_page(page)
            page.close()
            return result
        except Exception as exc:  # noqa: BLE001
            _LOG.error("[tesco] Product page failed: %s", exc)
            return None

    def _parse_detail_page(self, page: Page) -> SupermarketResult:
        """Parse Tesco product detail page."""
        name_el = page.query_selector("h1, [data-testid='product-title']")
        name = name_el.inner_text().strip() if name_el else ""

        price_el = page.query_selector("[data-testid='price'], .price")
        price = price_el.inner_text().strip() if price_el else ""

        desc_el = page.query_selector("[data-testid='product-description']")
        description = desc_el.inner_text().strip() if desc_el else ""

        return SupermarketResult(
            name=name,
            price=price,
            description=description,
            retailer="Tesco",
        )
