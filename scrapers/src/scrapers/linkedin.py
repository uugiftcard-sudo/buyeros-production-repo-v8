"""
LinkedIn scraper — public profile and keyword search.

Scrapes publicly visible profile data. Keyword search uses Google
site:linkedin.com/in queries as a discovery layer.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests

from src.models.linkedin import LinkedInProfile
from src.scrapers.base import BaseScraper
from src.utils.html import make_soup_htmlparser as make_soup

_LOG = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper[LinkedInProfile]):
    """
    LinkedIn public profile scraper.

    Example:
        scraper = LinkedInScraper(delay=3.0)
        profile = scraper.scrape_item("https://uk.linkedin.com/in/johndoe")
    """

    name = "linkedin"

    def scrape_item(self, url: str) -> LinkedInProfile | None:
        """Fetch and parse a single LinkedIn profile URL."""
        # Clean URL
        url = re.split(r"\?", url)[0].rstrip("/")

        resp = self._get(url)
        if resp is None:
            return None

        soup = make_soup(resp.text)
        return self._parse_profile(soup, url)

    def _parse_profile(self, soup: Any, url: str) -> LinkedInProfile:
        """Parse a BeautifulSoup tree into a LinkedInProfile."""
        profile = LinkedInProfile(profile_url=url)

        # Name — primary <h1>
        name_tag = soup.select_one("h1")
        if name_tag:
            profile.name = name_tag.get_text(strip=True)

        # Headline — multiple fallback selectors
        for sel in ("[class*='headline']", ".pv-top-card-v2-ctas"):
            tag = soup.select_one(sel)
            if tag:
                profile.headline = tag.get_text(strip=True)
                break

        # Fallback: og:description
        if not profile.headline:
            desc = soup.find("meta", property="og:description")
            if desc and desc.get("content"):
                profile.headline = desc["content"].strip().strip('"')

        # Location
        for sel in ("[class*='location']", "[class*='geo']"):
            tag = soup.select_one(sel)
            if tag:
                profile.location = tag.get_text(strip=True)
                break

        # Industry
        ind_tag = soup.select_one("[class*='industry']")
        if ind_tag:
            profile.industry = ind_tag.get_text(strip=True)

        # Company — extract from headline patterns "Title at Company" / "Title · Company"
        if profile.headline and not profile.company:
            parts = re.split(r"\s+at\s+|\s+@\s+|·\s+", profile.headline)
            if len(parts) > 1:
                profile.company = parts[-1].strip().strip('"')

        # About
        about_tag = soup.select_one("[class*='about'], [class*='summary']")
        if about_tag:
            profile.about = about_tag.get_text(strip=True)
        else:
            desc = soup.find("meta", property="og:description")
            if desc and desc.get("content"):
                profile.about = desc["content"].strip()

        # Connections (sometimes visible on public profiles)
        conn_tag = soup.select_one("[class*='connection']")
        if conn_tag:
            profile.connections = conn_tag.get_text(strip=True)

        # HTML preview
        main_tag = soup.select_one("main, [class*='profile']")
        if main_tag:
            profile.raw_html_preview = main_tag.get_text()[:200].strip()

        return profile

    def scrape_batch(self, urls: list[str]) -> list[LinkedInProfile]:
        """Scrape multiple profile URLs."""
        self.reset()
        result = super().scrape_batch(urls)
        return result.items

    def search_by_keyword_google(
        self,
        keyword: str,
        limit: int = 10,
        delay: float | None = None,
    ) -> list[str]:
        """
        Discover LinkedIn profile URLs via Google search.

        Uses a simple HTTP GET + HTML parse. Rate limits apply.
        For production use, consider SerpAPI or Google Custom Search API.
        """
        query = f"site:linkedin.com/in {keyword}"
        encoded_q = requests.utils.quote(query)
        url = f"https://www.google.com/search?q={encoded_q}&num={min(limit, 10)}"

        resp = self._get(url)
        if resp is None:
            return []

        soup = make_soup(resp.text)
        links: list[str] = []
        seen: set[str] = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "/url?q=" not in href:
                continue
            match = re.search(r"/url\?q=([^&]+)", href)
            if not match:
                continue
            raw = requests.utils.unquote(match.group(1))
            if "/in/" in raw and raw not in seen:
                clean = re.split(r"\?", raw)[0].rstrip("/")
                seen.add(clean)
                links.append(clean)
                if len(links) >= limit:
                    break

        _LOG.info(f"Google search for '{keyword}' returned {len(links)} URLs")
        if delay is None:
            delay = self.delay
        time.sleep(delay)
        return links

    def scrape(self, urls: list[str]) -> list[LinkedInProfile]:
        """Scrape a list of profile URLs (convenience wrapper)."""
        return self.scrape_batch(urls)
