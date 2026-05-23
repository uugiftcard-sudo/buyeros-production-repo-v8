"""
Vinted (vinted.co.uk) scraper — fashion resale marketplace.

Supports:
  - Keyword / filtered search via the Vinted web API
  - Individual item detail scraping via HTML
  - Seller profile scraping via HTML

Uses the Vinted internal web API (api.vinted.com / www.vinted.co.uk/api/v2)
as the primary source, falling back to HTML parsing when needed.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

from src.models.vinted import (
    Gender,
    ItemCondition,
    ItemStatus,
    SellerResult,
    VintedProduct,
)
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup, text

_LOG = logging.getLogger(__name__)

_WEB_BASE = "https://www.vinted.co.uk"
_API_BASE = f"{_WEB_BASE}/api/v2"

# Vinted API headers — mimics the official web client
_API_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": _WEB_BASE,
    "X-Requested-With": "XMLHttpRequest",
}

# Page-size used for search pagination
_PAGE_SIZE = 50

# Condition label → enum mapping (used in HTML fallback)
_CONDITION_MAP: dict[str, ItemCondition] = {
    "new with tags": ItemCondition.NEW_WITH_TAGS,
    "new without tags": ItemCondition.NEW_WITHOUT_TAGS,
    "very good": ItemCondition.VERY_GOOD,
    "good": ItemCondition.GOOD,
    "satisfactory": ItemCondition.SATISFACTORY,
}


class VintedScraper(BaseScraper[VintedProduct]):
    """
    Vinted fashion marketplace scraper.

    Example:
        scraper = VintedScraper(delay=2.0)
        items = scraper.scrape_search("gucci bag", pages=2)
        product = scraper.scrape_product("https://www.vinted.co.uk/items/1234567")
        seller = scraper.scrape_user("johndoe")
    """

    name = "vinted"

    def __init__(
        self,
        delay: float = 2.0,
        country: str = "gb",
        currency: str = "GBP",
    ) -> None:
        """
        Args:
            delay: Seconds between requests (respects Vinted rate limits).
            country: Two-letter country code for search locale (gb, de, fr, etc.).
            currency: Currency for prices returned in results.
        """
        super().__init__(delay=delay)
        self.country = country
        self.currency = currency
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept": "application/json, text/html, */*;q=0.8",
            }
        )

    # ── BaseScraper contract ────────────────────────────────────

    def scrape_item(self, url: str) -> VintedProduct | None:
        """Scrape a single item from its public URL."""
        return self.scrape_product(url)

    # ── Public API ──────────────────────────────────────────────

    def scrape_search(
        self,
        keyword: str,
        pages: int = 1,
        filters: dict[str, Any] | None = None,
    ) -> list[VintedProduct]:
        """
        Search Vinted listings by keyword with optional filters.

        Args:
            keyword: Search query (brand, item type, style, etc.).
            pages: Number of result pages to fetch (50 items/page).
            filters: Optional dict with keys:
                - brand: brand name or ID
                - size: size label (e.g. "M", "38")
                - condition: ItemCondition value or string
                - min_price: float
                - max_price: float
                - category: category ID (int)
                - gender: Gender value or string (male/female/unisex)

        Returns:
            List of VintedProduct objects, newest first.
        """
        filters = filters or {}
        results: list[VintedProduct] = []

        for page in range(1, pages + 1):
            self._wait()
            items = self._search_page(keyword, page, filters)
            if not items:
                _LOG.info(f"[Vinted] No results on page {page} — stopping")
                break

            for raw in items:
                product = self._parse_search_item(raw)
                product.search_keyword = keyword
                results.append(product)

            _LOG.info(f"[Vinted] Page {page}: fetched {len(items)} items")

            if len(items) < _PAGE_SIZE:
                break  # Last page

        _LOG.info(f"[Vinted] Total: {len(results)} items for '{keyword}'")
        return results

    def scrape_product(self, url: str) -> VintedProduct | None:
        """
        Fetch full detail for a single Vinted listing.

        Tries the API first (fast), then falls back to HTML parsing.
        """
        # Extract item ID from URL for API lookup
        item_id = self._extract_item_id(url)
        if not item_id:
            _LOG.warning(f"[Vinted] Could not extract item ID from URL: {url}")
            return None

        # Try API first
        product = self._fetch_item_via_api(item_id)
        if product:
            product.url = url
            return product

        # Fallback to HTML
        return self._fetch_item_via_html(url)

    def scrape_user(self, username: str) -> SellerResult | None:
        """
        Fetch a Vinted seller's public profile.

        Args:
            username: Vinted username (from a listing's seller section).

        Returns:
            SellerResult or None on failure.
        """
        if not username:
            return None

        url = f"{_WEB_BASE}/member/{username}"
        return self._fetch_user_via_html(url)

    # ── Internal: search ────────────────────────────────────────

    def _search_page(
        self,
        keyword: str,
        page: int,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch one page of search results from the Vinted API."""
        params: dict[str, Any] = {
            "search_text": keyword,
            "page": page,
            "per_page": _PAGE_SIZE,
            "order": "newest_first",
        }
        params.update(self._build_filter_params(filters))

        try:
            resp = self.session.get(
                f"{_API_BASE}/catalog/items",
                params=params,
                headers=_API_HEADERS,
                timeout=20,
            )
            if resp.status_code != 200:
                _LOG.warning(f"[Vinted API] Search returned {resp.status_code}")
                return []

            data = resp.json()
            items = data.get("items", [])
            if isinstance(items, list):
                return items

        except requests.RequestException as e:
            _LOG.error(f"[Vinted API] Search request failed: {e}")

        return []

    def _build_filter_params(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Convert the public filter dict to Vinted API query params."""
        params: dict[str, Any] = {}

        brand = filters.get("brand")
        if brand:
            params["brand_id[]"] = brand if str(brand).isdigit() else ""
            if not params["brand_id[]"]:
                params["search_text"] = filters.get("search_text", "")
                params["brand_name"] = brand

        size = filters.get("size")
        if size:
            params["size_id[]"] = size

        condition = filters.get("condition")
        if condition:
            if isinstance(condition, ItemCondition):
                params["status[]"] = condition.value
            else:
                params["status[]"] = condition

        min_price = filters.get("min_price")
        if min_price is not None:
            params["price_min"] = str(min_price)

        max_price = filters.get("max_price")
        if max_price is not None:
            params["price_max"] = str(max_price)

        category = filters.get("category")
        if category:
            params["catalog[]"] = category

        gender = filters.get("gender")
        if gender:
            if isinstance(gender, Gender):
                params["gender"] = gender.value
            else:
                params["gender"] = str(gender)

        return params

    # ── Internal: item detail ───────────────────────────────────

    def _fetch_item_via_api(self, item_id: str) -> VintedProduct | None:
        """Fetch item detail from the Vinted item API endpoint."""
        try:
            resp = self.session.get(
                f"{_API_BASE}/items/{item_id}",
                headers=_API_HEADERS,
                timeout=20,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            item = data.get("item") or data.get("items", [{}])[0] if data.get("items") else {}
            return self._parse_search_item(item) if item else None

        except requests.RequestException as e:
            _LOG.warning(f"[Vinted API] Item fetch failed: {e}")
            return None

    def _fetch_item_via_html(self, url: str) -> VintedProduct | None:
        """Parse item detail from the public HTML page."""
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            soup = make_soup(resp.text)
            return self._parse_item_html(soup, url)

        except requests.RequestException as e:
            _LOG.error(f"[Vinted HTML] Item fetch failed for {url}: {e}")
            return None

    def _parse_search_item(self, raw: dict[str, Any]) -> VintedProduct:
        """Map a raw Vinted API dict to a VintedProduct."""
        p = VintedProduct()
        p.item_id = str(raw.get("id", ""))
        p.url = raw.get("url", "") or f"{_WEB_BASE}/items/{p.item_id}"

        p.title = raw.get("title", "")

        # Brand
        brand = raw.get("brand", {}) or {}
        if isinstance(brand, dict):
            p.brand_id = brand.get("id", 0) or 0
            p.brand_name = brand.get("name", "") or ""
        elif isinstance(brand, str):
            p.brand_name = brand

        # Sizes
        size_data = raw.get("size", {}) or {}
        if isinstance(size_data, dict):
            p.size = size_data.get("title", "") or ""
        elif isinstance(size_data, str):
            p.size = size_data

        # Condition
        status_label = raw.get("status", "")
        p.condition = self._parse_condition(status_label)

        # Pricing
        price_data = raw.get("price", {}) or {}
        if isinstance(price_data, dict):
            p.price = float(price_data.get("amount", 0) or 0) / 100
            p.currency = price_data.get("currency_code", self.currency)
            orig = price_data.get("original_price", {})
            if isinstance(orig, dict) and orig.get("amount"):
                p.original_price = float(orig["amount"]) / 100
        elif isinstance(price_data, (int, float)):
            p.price = float(price_data)

        p.is_discounted = p.original_price > 0 and p.price < p.original_price

        # Status
        p.status = self._map_status(raw.get("is_reserved"), raw.get("is_sold"))

        # Photos
        photos_raw: list[dict[str, Any]] = raw.get("photos", [])
        p.photos = [
            photo.get("full_size_url", "")
            or photo.get("url", "")
            for photo in photos_raw
            if photo.get("full_size_url") or photo.get("url")
        ]
        if not p.photos and raw.get("photo"):
            p.photos = [raw["photo"].get("url", "")]

        # Seller
        user = raw.get("user", {}) or {}
        p.seller_id = str(user.get("id", ""))
        p.seller_username = user.get("login", "") or user.get("username", "")
        p.seller_rating = float(user.get("feedback_reputation", 0) or 0)
        p.seller_reviews = int(user.get("feedback_count", 0) or 0)

        # Engagement
        p.views = int(raw.get("view_count", 0) or 0)
        p.watchers = int(raw.get("favourite_count", 0) or 0)

        # Timestamps
        p.posted_at = self._parse_vinted_time(raw.get("created_at"))
        p.updated_at = self._parse_vinted_time(raw.get("updated_at"))

        # Category
        categories: list[dict[str, Any]] = raw.get("catalog_categories", []) or []
        if categories:
            p.category = categories[0].get("name", "")
            if len(categories) > 1:
                p.subcategory = categories[1].get("name", "")

        # Color & material
        p.color = raw.get("color", "") or ""
        p.material = raw.get("material", "") or ""

        # Gender
        gender_val = raw.get("gender")
        if gender_val:
            try:
                p.gender = Gender(gender_val)
            except ValueError:
                pass

        return p

    def _parse_item_html(self, soup, url: str) -> VintedProduct | None:
        """Parse item detail from BeautifulSoup of the public listing page."""
        p = VintedProduct()
        p.url = url
        p.item_id = self._extract_item_id(url)

        # Title
        title_el = soup.select_one(
            "[class*='item-detail'], "
            "[class*='ItemDetails'], "
            "[class*='item-title'], "
            "h1[class*='title'], "
            "h1"
        )
        p.title = text(title_el) if title_el else ""

        # Price
        price_el = soup.select_one(
            "[class*='item-price'], "
            "[class*='ItemPrice'], "
            "[class*='price'], "
            "[data-testid='price']"
        )
        if price_el:
            price_str = text(price_el)
            m = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
            if m:
                try:
                    p.price = float(m.group())
                except ValueError:
                    pass

        # Brand
        brand_el = soup.select_one(
            "[class*='brand'], [class*='Brand'], a[href*='/brand/']"
        )
        if brand_el:
            p.brand_name = text(brand_el)

        # Size
        size_el = soup.select_one(
            "[class*='size'], [class*='Size']"
        )
        if size_el:
            p.size = text(size_el)

        # Condition
        cond_el = soup.select_one(
            "[class*='condition'], [class*='Condition']"
        )
        if cond_el:
            p.condition = self._parse_condition(text(cond_el).lower())

        # Photos — look for <img> tags in gallery
        photo_els = soup.select(
            "[class*='photo'], [class*='image'], "
            "[class*='gallery'] img, [class*='slider'] img, "
            "[data-testid='photo']"
        )
        p.photos = [
            img.get("src", "") or img.get("data-src", "")
            for img in photo_els
            if img.get("src") or img.get("data-src")
        ]

        # Seller
        seller_el = soup.select_one("[class*='seller'], [class*='UserInfo']")
        if seller_el:
            p.seller_username = text(seller_el.select_one("a, [class*='name']"))

        # Description
        desc_el = soup.select_one(
            "[class*='description'], [class*='Description'], "
            "[class*='item-description']"
        )
        if desc_el:
            p.description = desc_el.get_text(strip=True)

        # Try to extract embedded JSON data
        json_data = self._extract_page_data(soup)
        if json_data:
            # Merge API-like data on top of HTML-parsed values
            temp = self._parse_search_item(json_data)
            for field in ("item_id", "brand_name", "brand_id", "size", "color",
                           "material", "gender", "status", "views", "watchers",
                           "posted_at", "updated_at", "seller_id", "seller_username",
                           "seller_rating", "seller_reviews", "photos",
                           "original_price", "is_discounted"):
                val = getattr(temp, field)
                if val and val != getattr(p, field):
                    setattr(p, field, val)

        return p

    # ── Internal: seller profile ──────────────────────────────────

    def _fetch_user_via_html(self, url: str) -> SellerResult | None:
        """Parse seller profile from the public member page."""
        s = SellerResult()
        s.profile_url = url

        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            soup = make_soup(resp.text)

            # Username from URL or page
            s.username = url.rstrip("/").split("/")[-1]

            # Real name / display name
            name_el = soup.select_one(
                "[class*='user-name'], [class*='UserName'], "
                "[class*='member-name'], [class*='profile-name']"
            )
            if name_el:
                s.real_name = text(name_el)

            # Stats
            stats = soup.select("[class*='stat'], [class*='count'], [class*='number']")
            for stat in stats:
                stat_text = text(stat).lower()
                if "follower" in stat_text:
                    m = re.search(r"\d+", text(stat))
                    if m:
                        s.follower_count = int(m.group())
                elif "item" in stat_text or "listing" in stat_text:
                    m = re.search(r"\d+", text(stat))
                    if m:
                        s.item_count = int(m.group())
                elif "review" in stat_text:
                    m = re.search(r"\d+", text(stat))
                    if m:
                        s.review_count = int(m.group())

            # Rating
            rating_el = soup.select_one("[class*='rating'], [class*='score']")
            if rating_el:
                m = re.search(r"[\d.]+", text(rating_el))
                if m:
                    s.rating = float(m.group())

            # Location
            loc_el = soup.select_one("[class*='location'], [class*='Location']")
            if loc_el:
                s.location = text(loc_el)

            # Member since
            since_el = soup.select_one("[class*='since'], [class*='joined']")
            if since_el:
                s.member_since = text(since_el)

            # Verified badge
            s.is_verified = bool(
                soup.select_one("[class*='verified'], [class*='TrustedSeller']")
            )

            # Photo
            photo_el = soup.select_one(
                "[class*='avatar'] img, [class*='Avatar'] img, "
                "img[class*='profile']"
            )
            if photo_el:
                s.photo_url = photo_el.get("src", "")

            _LOG.info(f"[Vinted] Seller {s.username}: rating={s.rating}, items={s.item_count}")
            return s

        except requests.RequestException as e:
            _LOG.error(f"[Vinted] Seller fetch failed for {url}: {e}")
            return None

    # ── Internal: utilities ───────────────────────────────────────

    def _extract_item_id(self, url: str) -> str:
        """Extract the numeric item ID from a Vinted item URL."""
        # https://www.vinted.co.uk/items/1234567
        m = re.search(r"/items/(\d+)", url)
        if m:
            return m.group(1)
        return ""

    def _parse_condition(self, label: str) -> ItemCondition | None:
        """Map a Vinted condition/status label to an ItemCondition enum."""
        if not label:
            return None
        label_lower = label.lower().strip()
        return _CONDITION_MAP.get(label_lower)

    def _map_status(self, is_reserved: bool, is_sold: bool) -> ItemStatus:
        """Map Vinted boolean flags to ItemStatus enum."""
        if is_reserved:
            return ItemStatus.RESERVED
        if is_sold:
            return ItemStatus.SOLD
        return ItemStatus.ACTIVE

    def _parse_vinted_time(self, ts: str | None) -> str:
        """Normalise Vinted ISO timestamp to YYYY-MM-DD HH:MM:SS."""
        if not ts:
            return ""
        # ts is like "2024-03-15T12:34:56Z"
        m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", str(ts))
        if m:
            return f"{m.group(1)} {m.group(2)}"
        return str(ts)

    def _extract_page_data(self, soup) -> dict[str, Any]:
        """
        Try to extract the embedded JSON object from the page's
        <script> tags that Vinted uses to bootstrap item data.
        """
        import json

        scripts = soup.find_all("script")
        for script in scripts:
            content = script.string or ""
            if '"item":{' not in content and '"items":[' not in content:
                continue
            # Look for a top-level "item" or "items" object literal
            m = re.search(r'\{"item"\s*:\s*(\{.*?\})\s*\}', content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        return {}
