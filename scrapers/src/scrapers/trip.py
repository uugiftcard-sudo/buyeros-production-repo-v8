"""
Trip.com scraper — flights, hotels, and attractions.

Extracts data from Trip.com search pages using JSON-script parsing
with HTML fallback.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any

import requests

from src.models.trip import AttractionResult, FlightResult, HotelResult
from src.utils.html import make_soup

_LOG = logging.getLogger(__name__)

_BASE_URL = "https://www.trip.com"


class TripScraper:
    """
    Trip.com scraper for flights, hotels, and attractions.

    Example:
        scraper = TripScraper()
        flights = scraper.search_flights("LHR", "NRT", "2025-06-15")
        hotels = scraper.search_hotels("london", checkin="2025-06-15", checkout="2025-06-18")
    """

    name = "trip"

    def __init__(self, delay: float = 2.0) -> None:
        self.delay = delay

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": _BASE_URL + "/",
            "Origin": _BASE_URL,
        }

    def _fetch(self, url: str, params: dict[str, Any] | None = None) -> Any | None:
        """GET with retry and backoff."""
        for attempt in range(3):
            try:
                resp = requests.get(url, params=params, headers=self._headers(), timeout=15)
                if resp.status_code in (403, 429, 999):
                    backoff = 5 + attempt * 5 + (attempt * 2)
                    _LOG.warning(f"Blocked ({resp.status_code}), sleeping {backoff}s")
                    time.sleep(backoff)
                    continue
                resp.raise_for_status()
                return make_soup(resp.text)
            except requests.RequestException as e:
                if attempt < 2:
                    wait = (2**attempt) + 1
                    _LOG.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {wait}s")
                    time.sleep(wait)
                else:
                    _LOG.error(f"Final failure fetching {url}: {e}")
        return None

    @staticmethod
    def _price(text: str) -> str:
        """Extract price string from text."""
        if not text:
            return ""
        m = re.search(r"¥?\s*([\d,]+\.?\d*)", text)
        return m.group(1) if m else text.strip()

    @staticmethod
    def _safe(d: dict[str, Any], *keys: str, default: str = "") -> str:
        """Safely navigate a nested dict."""
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k, {})
            else:
                return default
        return str(d) if d else default

    # ── Flights ─────────────────────────────────────────────────

    def search_flights(
        self,
        depart_code: str,
        arrive_code: str,
        depart_date: str,
        return_date: str = "",
        cabin_class: str = "economy",
        currency: str = "CNY",
    ) -> list[FlightResult]:
        """
        Search flights by IATA airport codes.

        Args:
            depart_code: Departure airport IATA code (e.g. "LHR")
            arrive_code: Arrival airport IATA code (e.g. "NRT")
            depart_date: Departure date in YYYY-MM-DD format
            return_date: Return date (optional, for round trips)
            cabin_class: Cabin class (economy, business, first)
            currency: Currency code (default CNY)
        """
        search_url = (
            f"{_BASE_URL}/flights/{depart_code}-{arrive_code}/"
            f"{depart_date}?cabin=y&adult=1&child=0&infant=0"
        )
        _LOG.info(f"Searching flights: {depart_code} → {arrive_code} | {depart_date}")
        results: list[FlightResult] = []
        soup = self._fetch(search_url)
        if soup is None:
            return results

        now = datetime.now().isoformat(timespec="seconds")

        # Method 1: JSON script extraction
        for script in soup.find_all("script"):
            text = script.string or ""
            if "flightList" not in text and "flightNo" not in text:
                continue

            for match in re.finditer(r'"flightList"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL):
                try:
                    flight_data = __import__("json").loads(match.group(1))
                    if isinstance(flight_data, list):
                        for f in flight_data[:20]:
                            r = FlightResult(
                                search_url=search_url, searched_at=now, currency=currency
                            )
                            r.airline = f.get("airlineName", "") or self._safe(f, "airline", "name")
                            r.flight_no = f.get("flightNo", "")
                            r.depart_time = f.get("departureDateTime", "")
                            r.arrive_time = f.get("arrivalDateTime", "")
                            r.depart_airport = f.get("departureAirport", "") or self._safe(
                                f, "departureAirport", "name"
                            )
                            r.arrive_airport = f.get("arrivalAirport", "") or self._safe(
                                f, "arrivalAirport", "name"
                            )
                            r.duration = f.get("duration", "")
                            r.stops = str(f.get("stops", "0"))
                            r.cabin_class = cabin_class
                            price = f.get("price") or self._safe(f, "priceInfo", "price")
                            r.price = str(price) if price else ""
                            results.append(r)
                except Exception:  # noqa: BLE001
                    pass

        # Method 2: HTML fallback
        if not results:
            _LOG.info("JSON extraction empty, falling back to HTML parsing")
            cards = soup.select("[class*='flight'], [class*='cabin'], .flight-card")
            for card in cards[:15]:
                r = FlightResult(search_url=search_url, searched_at=now, currency=currency)
                r.cabin_class = cabin_class
                for sel, field in (
                    ("[class*='airline']", "airline"),
                    ("[class*='flight-no']", "flight_no"),
                ):
                    tag = card.select_one(sel)
                    if tag:
                        setattr(r, field, tag.get_text(strip=True)[:50])
                for sel, field in (
                    ("[class*='depart']", "depart_time"),
                    ("[class*='arrive']", "arrive_time"),
                ):
                    tag = card.select_one(sel)
                    if tag:
                        setattr(r, field, tag.get_text(strip=True))
                price_tag = card.select_one("[class*='price']")
                if price_tag:
                    r.price = self._price(price_tag.get_text())
                if r.airline or r.flight_no or r.price:
                    results.append(r)

        _LOG.info(f"Found {len(results)} flight results")
        return results

    # ── Hotels ─────────────────────────────────────────────────

    def search_hotels(
        self,
        city_pinyin: str,
        keyword: str = "",
        checkin: str = "",
        checkout: str = "",
        currency: str = "CNY",
    ) -> list[HotelResult]:
        """
        Search hotels in a city.

        Args:
            city_pinyin: City pinyin (e.g. "london", "shanghai")
            keyword: Optional search keyword
            checkin: Check-in date YYYY-MM-DD
            checkout: Check-out date YYYY-MM-DD
            currency: Currency code
        """
        params: dict[str, str] = {}
        if keyword:
            params["kwd"] = keyword
        if checkin:
            params["checkin"] = checkin
        if checkout:
            params["checkout"] = checkout

        search_url = f"{_BASE_URL}/hotels/{city_pinyin}"
        if params:
            search_url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

        _LOG.info(f"Searching hotels: {city_pinyin}")
        results: list[HotelResult] = []
        soup = self._fetch(search_url)
        if soup is None:
            return results

        now = datetime.now().isoformat(timespec="seconds")

        for script in soup.find_all("script"):
            text = script.string or ""
            if "hotelList" not in text and "hotelName" not in text:
                continue

            for match in re.finditer(r'"hotelList"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL):
                try:
                    hotel_data = __import__("json").loads(match.group(1))
                    if isinstance(hotel_data, list):
                        for h in hotel_data[:20]:
                            r = HotelResult(searched_at=now, currency=currency)
                            r.name = h.get("hotelName", "")
                            r.star_rating = str(h.get("starRating", ""))
                            r.user_rating = str(h.get("rating", ""))
                            r.review_count = str(h.get("reviewCount", ""))
                            r.location = h.get("locationName", "")
                            r.district = h.get("districtName", "")
                            price = h.get("price")
                            r.price = str(price) if price else ""
                            r.original_price = str(h.get("originalPrice", ""))
                            r.discount = h.get("discountText", "")
                            facilities = h.get("facilityList") or []
                            r.amenities = ",".join(str(f) for f in facilities[:8])
                            r.has_breakfast = "Yes" if h.get("hasBreakfast") else "No"
                            r.free_cancellation = "Yes" if h.get("freeCancellation") else "No"
                            img = h.get("imageUrl") or (
                                h.get("hotelImage", [{}])[0].get("url")
                                if h.get("hotelImage")
                                else ""
                            )
                            r.image_url = img if isinstance(img, str) else ""
                            du = h.get("detailUrl", "")
                            r.detail_url = (_BASE_URL + du) if not du.startswith("http") else du
                            if r.name or r.price:
                                results.append(r)
                except Exception:  # noqa: BLE001
                    pass

        if not results:
            _LOG.info("HTML fallback for hotel parsing")
            for card in soup.select("[class*='hotel'], [class*='list-item'], .hotel-card")[:15]:
                r = HotelResult(searched_at=now, currency=currency)
                name_tag = card.select_one("h3, [class*='name'], [class*='title']")
                if name_tag:
                    r.name = name_tag.get_text(strip=True)
                price_tag = card.select_one("[class*='price'], strong")
                if price_tag:
                    r.price = self._price(price_tag.get_text())
                if r.name:
                    results.append(r)

        _LOG.info(f"Found {len(results)} hotel results")
        return results

    # ── Attractions ─────────────────────────────────────────────

    def search_attractions(
        self,
        city_pinyin: str,
        keyword: str = "",
        city_name: str = "",
        currency: str = "CNY",
    ) -> list[AttractionResult]:
        """Search attractions in a city."""
        params: dict[str, str] = {}
        if keyword:
            params["kwd"] = keyword
        search_url = f"{_BASE_URL}/attractions/{city_pinyin}"
        if params:
            search_url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

        _LOG.info(f"Searching attractions: {city_pinyin} {keyword}")
        results: list[AttractionResult] = []
        soup = self._fetch(search_url)
        if soup is None:
            return results

        now = datetime.now().isoformat(timespec="seconds")

        for script in soup.find_all("script"):
            text = script.string or ""
            if "poiList" not in text and "attraction" not in text.lower():
                continue

            for match in re.finditer(r'"poiList"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL):
                try:
                    data = __import__("json").loads(match.group(1))
                    if isinstance(data, list):
                        for a in data[:20]:
                            r = AttractionResult(searched_at=now, currency=currency)
                            r.name = a.get("name", "")
                            r.category = a.get("categoryName", "")
                            r.location = a.get("address", "")
                            r.city = city_name or city_pinyin
                            r.rating = str(a.get("rating", ""))
                            r.review_count = str(a.get("reviewCount", ""))
                            r.ticket_price = str(a.get("price", ""))
                            r.description = a.get("description", "")[:200]
                            r.opening_hours = a.get("openTime", "")
                            r.image_url = a.get("imageUrl", "")
                            du = a.get("detailUrl", "")
                            r.detail_url = (_BASE_URL + du) if not du.startswith("http") else du
                            if r.name:
                                results.append(r)
                except Exception:  # noqa: BLE001
                    pass

        if not results:
            for card in soup.select("[class*='poi'], [class*='attraction']")[:15]:
                r = AttractionResult(searched_at=now, currency=currency)
                tag = card.select_one("h3, [class*='name'], a")
                if tag:
                    r.name = tag.get_text(strip=True)
                if r.name:
                    results.append(r)

        _LOG.info(f"Found {len(results)} attraction results")
        return results
