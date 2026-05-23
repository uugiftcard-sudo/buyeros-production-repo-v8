"""Unit tests for src/scrapers/async_base.py."""

import pytest

from src.scrapers.async_base import AsyncBaseScraper


class ConcreteAsyncScraper(AsyncBaseScraper[dict]):
    """Minimal concrete subclass for testing."""

    name = "test_async"

    async def scrape_item(self, url: str, client) -> dict | None:
        # Always succeed with a dummy item
        return {"url": url, "title": "Test Item"}


class FailingAsyncScraper(AsyncBaseScraper[dict]):
    """Always returns None to test error path."""

    name = "test_failing"

    async def scrape_item(self, url: str, client) -> dict | None:
        return None


class TestAsyncBaseScraper:
    def test_name_attribute_is_set(self):
        """Subclass must define a `name` class attribute."""
        scraper = ConcreteAsyncScraper()
        assert scraper.name == "test_async"

    def test_delay_defaults_from_config(self):
        """delay is loaded from config if not explicitly passed."""
        scraper = ConcreteAsyncScraper()
        assert isinstance(scraper.delay, float)
        assert scraper.delay >= 0

    def test_explicit_delay_overrides_config(self):
        """Passing delay=0.5 overrides the config value."""
        scraper = ConcreteAsyncScraper(delay=0.5)
        assert scraper.delay == 0.5

    def test_max_retries_defaults_from_config(self):
        """max_retries is loaded from config."""
        scraper = ConcreteAsyncScraper()
        assert isinstance(scraper.max_retries, int)
        assert scraper.max_retries >= 1

    def test_result_property_returns_scrape_result(self):
        """result property returns the current ScrapeResult."""
        scraper = ConcreteAsyncScraper()
        result = scraper.result
        assert result is not None
        assert hasattr(result, "items")

    def test_reset_clears_results(self):
        """reset() clears the internal result."""
        scraper = ConcreteAsyncScraper()
        initial = scraper.result
        scraper.reset()
        assert scraper.result is not initial  # new object
        assert len(scraper.result.items) == 0

    def test_headers_includes_user_agent(self):
        """_headers() includes a User-Agent header."""
        scraper = ConcreteAsyncScraper()
        headers = scraper._headers()
        assert "User-Agent" in headers
        assert len(headers["User-Agent"]) > 10

    def test_headers_extra_headers_merged(self):
        """Extra headers passed to _headers() are included."""
        scraper = ConcreteAsyncScraper()
        headers = scraper._headers({"X-Custom": "value"})
        assert "X-Custom" in headers
        assert headers["X-Custom"] == "value"

    def test_random_ua_returns_string(self):
        """_random_ua() returns a non-empty string."""
        scraper = ConcreteAsyncScraper()
        ua = scraper._random_ua()
        assert isinstance(ua, str)
        assert len(ua) > 0
