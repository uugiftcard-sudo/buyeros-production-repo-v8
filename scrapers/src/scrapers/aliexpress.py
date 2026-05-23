"""
AliExpress product scraper — search results and item detail pages.

Supports the AliExpress open API (preferred) with HTML fallback.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import requests

from src.models.aliexpress import AliExpressProduct
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)

_ALI_BASE = "https://www.aliexpress.com"
_SEARCH_URL = "https://www.aliexpress.com/wholesale"
_ITEM_RE = re.compile(r"/item/(\d+)\.html")


class AliExpressScraper(BaseScraper[AliExpressProduct]):
    """
    AliExpress product scraper supporting keyword search and detail pages.

    Example:
        scraper = AliExpressScraper()
        products = scraper.scrape_search("laptop", pages=2)
        detail  = scraper.scrape_product("https://www.aliexpress.com/item/...")
    """

    name = "aliexpress"

    def __init__(
        self,
        domain: str = "com",
        delay: float = 2.0,
        max_retries: int | None = None,
    ) -> None:
        super().__init__(delay=delay, max_retries=max_retries)
        self.domain = domain
        self.base_url = _ALI_BASE
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": self.base_url,
            }
        )

    # ── Internal helpers ────────────────────────────────────────────

    def _random_ua(self) -> str:
        """Override to use session-level headers; UA is set in __init__."""
        import random
        from src.config import get_user_agents

        return random.choice(get_user_agents())

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build headers with a random User-Agent."""
        import random
        from src.config import get_user_agents

        base = {
            "User-Agent": random.choice(get_user_agents()),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": self.base_url,
        }
        if extra:
            base.update(extra)
        return base

    def _extract_product_id(self, url_or_text: str) -> str:
        """Pull product ID from an AliExpress item URL."""
        m = _ITEM_RE.search(url_or_text)
        return m.group(1) if m else ""

    def _parse_price(self, text: str) -> tuple[str, str, str]:
        """
        Parse price string into (current, original, currency).

        Handles formats like:
          US $12.99 - $15.99
          $12.99  (was  $19.99)
          ¥128.00
        """
        if not text:
            return "", "", ""

        # Strip "US " prefix that AliExpress sometimes adds
        text = text.replace("US ", "").strip()

        # Try "current - original" range format
        range_m = re.search(r"[\$\€\£\¥]?\s*([\d,]+\.?\d*)\s*-\s*[\$\€\£\¥]?\s*([\d,]+\.?\d*)", text)
        if range_m:
            curr = range_m.group(1)
            orig = range_m.group(2)
            sym = re.search(r"[\$€£¥]", text)
            curr_sym = sym.group(0) if sym else "$"
            return f"{curr_sym}{curr}", f"{curr_sym}{orig}", curr_sym

        # Try "was $X" format
        orig_m = re.search(r"(?:was|原价|original)\s*[:\-]?\s*[\$\€\£\¥]?\s*([\d,]+\.?\d*)", text, re.I)
        orig_val = orig_m.group(1) if orig_m else ""
        curr_m = re.search(r"[\$\€\£\¥]?\s*([\d,]+\.?\d*)", text)
        curr_val = curr_m.group(1) if curr_m else ""
        sym_m = re.search(r"[\$€£¥]", text)
        sym = sym_m.group(0) if sym_m else "$"
        return f"{sym}{curr_val}", f"{sym}{orig_val}" if orig_val else "", sym

    # ── BaseScraper abstract method ──────────────────────────────────

    def scrape_item(self, url: str) -> AliExpressProduct | None:
        """Alias for scrape_product() to satisfy BaseScraper."""
        return self.scrape_product(url)

    # ── Public API ──────────────────────────────────────────────────

    def scrape_search(self, keyword: str, pages: int = 1) -> list[AliExpressProduct]:
        """
        Search AliExpress by keyword across multiple result pages.

        Args:
            keyword: Search term
            pages: Number of pages to scrape (AliExpress shows ~20 items/page)

        Returns:
            List of AliExpressProduct objects.
        """
        all_results: list[AliExpressProduct] = []

        for page in range(1, pages + 1):
            _LOG.info(f"[AliExpress] Searching '{keyword}' page {page}/{pages}")
            items = self._fetch_search_page(keyword, page)
            all_results.extend(items)
            if page < pages:
                self._wait()

        return all_results

    def scrape_product(self, url: str) -> AliExpressProduct | None:
        """
        Scrape a single AliExpress product detail page.

        Args:
            url: Full AliExpress item URL (e.g. https://www.aliexpress.com/item/...)

        Returns:
            AliExpressProduct with full detail or None on failure.
        """
        product_id = self._extract_product_id(url)
        if not product_id:
            _LOG.warning(f"[AliExpress] Could not extract product ID from: {url}")
            return None

        p = AliExpressProduct()
        p.product_id = product_id
        p.url = url
        p.search_keyword = ""
        p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

        resp = self._get(url)
        if resp is None:
            return None

        soup = make_soup(resp.text)

        # Try to extract structured data from __INITIAL_DATA__ or window.* globals
        self._extract_from_window(soup, p)

        # Title
        title_tag = soup.select_one(
            "h1.product-title-text, "
            "[data-title='productTitle'], "
            ".product-title, "
            "h1[class*='title']"
        )
        if title_tag:
            p.title = title_tag.get_text(strip=True)

        # If still missing title, try JSON-LD
        if not p.title:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("name"):
                        p.title = data["name"]
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

        # Pricing block
        price_tag = soup.select_one(
            ".price-wrapper, .product-price-value, "
            "[class*='price'] span[class*='value'], "
            ".price-current"
        )
        if price_tag:
            curr, orig, sym = self._parse_price(price_tag.get_text(strip=True))
            if curr:
                p.price_current = curr
            if orig:
                p.price_original = orig
            if sym:
                p.currency = sym

        # Discount badge
        discount_tag = soup.select_one(
            ".discount, .product-discount, "
            "[class*='discount'] span, "
            ".discount-tag"
        )
        if discount_tag:
            p.discount_percent = discount_tag.get_text(strip=True)

        # Rating & reviews
        rating_tag = soup.select_one(
            ".review-wrapper .score, .rating-value, "
            "[class*='rating'] [class*='number'], "
            ".product-rating"
        )
        if rating_tag:
            p.rating = rating_tag.get_text(strip=True)

        reviews_tag = soup.select_one(
            ".review-count, .reviews-count, "
            "[class*='review'] [class*='count'], "
            "#reviews-count"
        )
        if reviews_tag:
            p.review_count = reviews_tag.get_text(strip=True)

        # Orders / sold
        orders_tag = soup.select_one(
            ".order-count, .sold-count, "
            "[class*='order'] [class*='count'], "
            "#orders-count"
        )
        if orders_tag:
            p.orders_count = orders_tag.get_text(strip=True)

        # Store info
        store_tag = soup.select_one(
            ".store-name, .seller-name, "
            "[class*='store'] [class*='name'], "
            "[class*='seller'] [class*='name']"
        )
        if store_tag:
            p.store_name = store_tag.get_text(strip=True)

        store_location_tag = soup.select_one(
            ".store-location, .seller-location, "
            "[class*='store'] [class*='location'], "
            "[class*='location']"
        )
        if store_location_tag:
            p.store_location = store_location_tag.get_text(strip=True)

        # Main image
        img_tag = soup.select_one(
            ".product-image img, "
            "#product-image img, "
            "[class*='product-image'] img"
        )
        if img_tag and img_tag.get("src"):
            p.main_image = img_tag["src"]

        # All images
        for img in soup.select(".product-image img, .image-thumbnails img"):
            src = img.get("src") or img.get("data-src") or ""
            if src and src not in p.images:
                p.images.append(src)

        # Variants (colour / size options)
        for option in soup.select(".sku-option, .product-sku-option, [class*='sku']"):
            variant: dict[str, Any] = {"type": "", "value": "", "available": True}
            type_tag = option.select_one("[class*='type'], [class*='label']")
            if type_tag:
                variant["type"] = type_tag.get_text(strip=True)
            val_tag = option.select_one("[class*='value'], [class*='option']")
            if val_tag:
                variant["value"] = val_tag.get_text(strip=True)
            if option.select_one(".disabled, .unavailable"):
                variant["available"] = False
            if variant["value"]:
                p.variants.append(variant)

        # Attributes (key specs)
        for row in soup.select(".attr-row, .product-property, [class*='property-line']"):
            key_tag = row.select_one(".attr-name, .property-title, [class*='label']")
            val_tag = row.select_one(".attr-value, .property-value, [class*='value']")
            if key_tag and val_tag:
                p.attributes.append(
                    {"key": key_tag.get_text(strip=True), "value": val_tag.get_text(strip=True)}
                )

        # Availability
        avail_tag = soup.select_one(
            ".product-status, .availability, [class*='stock'], "
            "[class*='availability']"
        )
        if avail_tag:
            text = avail_tag.get_text(strip=True).lower()
            p.availability = avail_tag.get_text(strip=True)
            p.in_stock = "out of stock" not in text and "unavailable" not in text

        # Shipping
        ship_tag = soup.select_one(
            ".shipping-price, .logistics-cost, "
            "[class*='shipping'] span, "
            ".product-shipping-info"
        )
        if ship_tag:
            ship_text = ship_tag.get_text(strip=True).lower()
            p.free_shipping = "free" in ship_text or "包邮" in ship_text
            p.shipping_price = ship_tag.get_text(strip=True)

        eta_tag = soup.select_one(
            ".shipping-eta, [class*='delivery'], "
            "[class*='eta'], "
            ".logistics-eta"
        )
        if eta_tag:
            p.shipping_eta = eta_tag.get_text(strip=True)

        # Category breadcrumb
        crumbs: list[str] = []
        for crumb in soup.select(".breadcrumb a, .breadcrumbs a, [class*='breadcrumb'] a"):
            text = crumb.get_text(strip=True)
            if text:
                crumbs.append(text)
        if crumbs:
            p.category = crumbs[0]
            p.subcategory = crumbs[-1] if len(crumbs) > 1 else ""

        _LOG.info(f"[AliExpress] Fetched detail: {p.title[:60] if p.title else '(no title)'} [{p.product_id}]")
        return p

    # ── Private helpers ─────────────────────────────────────────────

    def _fetch_search_page(self, keyword: str, page: int = 1) -> list[AliExpressProduct]:
        """Fetch and parse one search results page."""
        results: list[AliExpressProduct] = []

        # AliExpress search URL (mobile-friendly, less anti-bot friction)
        page_param = f"&page={page}" if page > 1 else ""
        url = f"{_ALI_BASE}/wholesale?SearchText={requests.utils.quote(keyword)}{page_param}"

        resp = self._get(url)
        if resp is None:
            return results

        soup = make_soup(resp.text)

        # Try structured JSON first (most reliable)
        json_results = self._extract_search_json(soup)
        if json_results:
            for item in json_results:
                item.search_keyword = keyword
                item.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")
                results.append(item)

        # HTML fallback
        if not results:
            results = self._parse_search_html(soup, keyword)

        _LOG.info(f"[AliExpress] Page {page}: found {len(results)} items for '{keyword}'")
        return results

    def _extract_search_json(self, soup) -> list[AliExpressProduct]:
        """
        Extract product data from embedded JSON script tags on search pages.
        AliExpress embeds listings as window.__AIO_NEXT_DATA__ or similar.
        """
        results: list[AliExpressProduct] = []

        # Pattern 1: window.__AIO_DATA__ or window.__NEXT_DATA__
        for script in soup.find_all("script"):
            text = script.string or ""
            if '"items"' not in text and '"products"' not in text:
                continue
            try:
                # Find the JSON object containing items
                for match in re.finditer(r'\["\w+ItemV2",\s*(\{.*?\})\]', text, re.DOTALL):
                    try:
                        data = json.loads(match.group(1))
                        products = data.get("items", data.get("products", []))
                        for pdata in products[:20]:
                            p = self._dict_to_product(pdata)
                            if p.product_id:
                                results.append(p)
                    except json.JSONDecodeError:
                        continue
            except Exception:  # noqa: BLE001
                continue

        # Pattern 2: searchResultItemBundles
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string or "")
                items = (
                    data.get("items", [])
                    or data.get("products", [])
                    or data.get("result", {}).get("items", [])
                )
                for pdata in items[:20]:
                    if isinstance(pdata, dict):
                        p = self._dict_to_product(pdata)
                        if p.product_id:
                            results.append(p)
            except (json.JSONDecodeError, TypeError):
                continue

        return results

    def _dict_to_product(self, data: dict[str, Any]) -> AliExpressProduct:
        """Convert a dict (from JSON) to an AliExpressProduct."""
        p = AliExpressProduct()

        p.product_id = str(data.get("itemId", data.get("productId", data.get("id", ""))))
        p.title = data.get("title", data.get("productTitle", ""))
        p.url = data.get("itemUrl", data.get("productUrl", ""))
        if p.url and not p.url.startswith("http"):
            p.url = f"{_ALI_BASE}{p.url}"

        # Pricing
        prices = data.get("prices", data.get("price", {}))
        if isinstance(prices, str):
            curr, orig, sym = self._parse_price(prices)
            p.price_current = curr
            p.price_original = orig
            p.currency = sym
        elif isinstance(prices, dict):
            p.price_current = prices.get("salePrice", prices.get("price", ""))
            p.price_original = prices.get("originalPrice", prices.get("wasPrice", ""))
            p.currency = prices.get("currencyCode", "USD")

        p.discount_percent = data.get("discount", data.get("discountRate", ""))
        p.rating = str(data.get("rating", data.get("starRating", "")))
        p.review_count = str(data.get("review", data.get("reviewCount", "")))
        p.orders_count = str(
            data.get("tradeCount", data.get("orders", data.get("sold", "")))
        )
        p.helpful_reviews = str(data.get("helpfulReviewCount", ""))

        store = data.get("store", data.get("seller", {}))
        p.store_name = store.get("name", store.get("storeName", ""))
        p.store_id = str(store.get("id", store.get("storeId", "")))
        p.store_rating = str(store.get("rating", ""))
        p.store_followers = str(store.get("followers", ""))
        p.store_location = store.get("location", store.get("country", ""))

        p.category = data.get("category", "")
        p.subcategory = data.get("subCategory", "")

        shipping = data.get("logistics", data.get("shipping", {}))
        if isinstance(shipping, dict):
            p.free_shipping = shipping.get("free", shipping.get("isFree", False))
            p.shipping_price = shipping.get("price", shipping.get("cost", ""))
            p.shipping_eta = shipping.get("eta", shipping.get("deliveryTime", ""))
        else:
            p.free_shipping = "free" in str(shipping).lower()
            p.shipping_price = str(shipping)

        images = data.get("images", data.get("imageList", []))
        if isinstance(images, list):
            p.images = [img.get("url", img) if isinstance(img, dict) else str(img) for img in images]
        if p.images:
            p.main_image = p.images[0]

        variants = data.get("variants", data.get("skuList", []))
        if isinstance(variants, list):
            for v in variants:
                if isinstance(v, dict):
                    p.variants.append(
                        {
                            "type": v.get("type", ""),
                            "value": v.get("value", v.get("skuAttr", "")),
                            "available": v.get("available", v.get("isAvailable", True)),
                        }
                    )

        p.availability = data.get("availability", data.get("stockStatus", ""))
        p.in_stock = data.get("inStock", data.get("available", True))

        return p

    def _parse_search_html(self, soup, keyword: str) -> list[AliExpressProduct]:
        """Parse search results from raw HTML (fallback)."""
        results: list[AliExpressProduct] = []

        # Try multiple listing selectors
        items = soup.select(
            ".list-item, .product-item, .items-list .item, "
            "[class*='list-item'], [class*='product-item'], "
            "article.product-card"
        )

        for item in items[:20]:
            p = AliExpressProduct()
            p.search_keyword = keyword
            p.scraped_at = time.strftime("%Y-%m-%d %H:%M:%S")

            # Product ID
            link = item.select_one("a[href*='/item/']")
            if link:
                href = link.get("href", "")
                p.url = href if href.startswith("http") else f"{_ALI_BASE}{href}"
                p.product_id = self._extract_product_id(href)

            # Title
            title_tag = item.select_one(
                "h3, h4, [class*='title'], [class*='name'], .product-title"
            )
            if title_tag:
                p.title = title_tag.get_text(strip=True)

            # Price
            price_tag = item.select_one(
                "[class*='price'], .price-current, "
                "span[class*='value'], [class*=' Price']"
            )
            if price_tag:
                curr, orig, sym = self._parse_price(price_tag.get_text(strip=True))
                p.price_current = curr
                p.price_original = orig
                p.currency = sym

            # Discount
            discount_tag = item.select_one("[class*='discount'], .sale-value")
            if discount_tag:
                p.discount_percent = discount_tag.get_text(strip=True)

            # Rating
            rating_tag = item.select_one("[class*='rating'] span, .rating-value, [class*='stars']")
            if rating_tag:
                p.rating = rating_tag.get_text(strip=True)

            # Reviews
            reviews_tag = item.select_one("[class*='review'] span, .review-count")
            if reviews_tag:
                p.review_count = reviews_tag.get_text(strip=True)

            # Orders
            orders_tag = item.select_one("[class*='order'], [class*='sold'], .sold-count")
            if orders_tag:
                p.orders_count = orders_tag.get_text(strip=True)

            # Image
            img_tag = item.select_one("img")
            if img_tag:
                p.main_image = img_tag.get("src") or img_tag.get("data-src") or ""

            # Store name
            store_tag = item.select_one("[class*='store'], [class*='seller']")
            if store_tag:
                p.store_name = store_tag.get_text(strip=True)

            if p.product_id or p.title:
                results.append(p)

        return results

    def _extract_from_window(self, soup, p: AliExpressProduct) -> None:
        """
        Extract structured data from window.__INITIAL_STATE__ or
        window.__PRELOADED_STATE__ embedded in HTML.
        """
        for script in soup.find_all("script"):
            text = script.string or ""
            if "__INITIAL_STATE__" not in text and "__PRELOADED_STATE__" not in text:
                continue
            try:
                # Find JSON object after the variable name
                m = re.search(
                    r'(?:__INITIAL_STATE__|__PRELOADED_STATE__)\s*=\s*({.*?})\s*;?\s*$',
                    text,
                    re.MULTILINE | re.DOTALL,
                )
                if not m:
                    continue
                data = json.loads(m.group(1))

                # Walk down to product data
                product_data = (
                    data.get("product", {})
                    or data.get("result", {}).get("product", {})
                    or data.get("data", {}).get("product", {})
                )
                if product_data:
                    extracted = self._dict_to_product(product_data)
                    # Only fill empty fields from window data
                    if not p.title and extracted.title:
                        p.title = extracted.title
                    if not p.price_current and extracted.price_current:
                        p.price_current = extracted.price_current
                    if not p.price_original and extracted.price_original:
                        p.price_original = extracted.price_original
                    if not p.currency or p.currency == "USD":
                        p.currency = extracted.currency
                    if not p.rating and extracted.rating:
                        p.rating = extracted.rating
                    if not p.review_count and extracted.review_count:
                        p.review_count = extracted.review_count
                    if not p.orders_count and extracted.orders_count:
                        p.orders_count = extracted.orders_count
                    if not p.store_name and extracted.store_name:
                        p.store_name = extracted.store_name
                    if not p.images and extracted.images:
                        p.images = extracted.images
                        p.main_image = extracted.main_image
            except (json.JSONDecodeError, TypeError):
                continue
