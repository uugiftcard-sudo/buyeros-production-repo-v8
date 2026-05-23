"""
HTML parsing helpers built on BeautifulSoup + lxml.

Provides safe selectors, text extraction, and JSON extraction
from script tags embedded in HTML.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


def make_soup(html: str) -> BeautifulSoup:
    """Parse HTML into a BeautifulSoup tree using lxml parser."""
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "lxml")


def make_soup_htmlparser(html: str) -> BeautifulSoup:
    """Parse HTML using the built-in html.parser (no lxml needed)."""
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")


def select_one(soup: BeautifulSoup, *selectors: str) -> Any | None:
    """
    Try each selector in order, return the first non-None result.
    Useful for multi-selector fallbacks in the same DOM region.
    """
    for sel in selectors:
        tag = soup.select_one(sel)
        if tag:
            return tag
    return None


def select_all(soup: BeautifulSoup, selector: str, limit: int = 0) -> list[Any]:
    """
    Select all elements matching `selector`, optionally limited to `limit` results.
    """
    results = soup.select(selector)
    if limit > 0:
        results = results[:limit]
    return results


def text(tag: Any | None, strip: bool = True) -> str:
    """Safely extract text from a BeautifulSoup tag."""
    if tag is None:
        return ""
    return tag.get_text(strip=strip)


def attr(tag: Any | None, key: str, default: str = "") -> str:
    """Safely read an attribute from a BeautifulSoup tag."""
    if tag is None:
        return default
    return tag.get(key, default)


def extract_json_from_scripts(
    soup: BeautifulSoup,
    key: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Find <script> tags containing a JSON array under `key`,
    parse and return the list of objects.

    Args:
        soup: Parsed BeautifulSoup tree
        key: Top-level JSON key to look for (e.g. "flightList", "hotelList")
        limit: Maximum number of objects to return

    Returns:
        List of parsed dict objects.
    """
    results: list[dict[str, Any]] = []
    scripts = soup.find_all("script")

    for script in scripts:
        text_content = script.string or ""
        if key not in text_content:
            continue

        # Try to extract the full JSON array for this key
        pattern = rf'"{key}"\s*:\s*(\[.*?\])\s*[,}}]'
        for match in re.finditer(pattern, text_content, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    results.extend(data[:limit])
                    if len(results) >= limit:
                        return results[:limit]
            except json.JSONDecodeError:
                # Fallback: try to find individual JSON objects
                pass

    return results[:limit] if results else []


def extract_jsonld_products(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """
    Extract all JSON-LD Product objects from a page.
    """
    results: list[dict[str, Any]] = []
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Product":
                        results.append(item)
            elif isinstance(data, dict) and data.get("@type") == "Product":
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            pass
    return results


def extract_price(text_content: str) -> str:
    """
    Extract the first numeric price from arbitrary text.
    Handles formats like: £12.99, $1,234.56, ¥ 1,200
    """
    if not text_content:
        return ""
    m = re.search(r"[\$£¥€]?\s*([\d,]+\.?\d*)", text_content)
    if m:
        return m.group(0).strip()
    return text_content.strip()


def clean_url(url: str, base: str = "") -> str:
    """
    Normalize a URL: strip query strings, trailing slashes.
    Optionally resolve relative URLs against `base`.
    """
    if not url:
        return ""
    url = re.split(r"\?", url)[0].rstrip("/")
    if not url.startswith("http") and base:
        from urllib.parse import urljoin

        url = urljoin(base, url)
    return url


def safe_int(text: str | None, default: int = 0) -> int:
    """Safely convert text to int, returning default on failure."""
    if not text:
        return default
    cleaned = re.sub(r"[^\d]", "", str(text))
    try:
        return int(cleaned)
    except ValueError:
        return default
