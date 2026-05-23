"""Unit tests for the BaseScraper class."""


from src.models.linkedin import LinkedInProfile
from src.scrapers.base import BaseScraper


class DummyScraper(BaseScraper[LinkedInProfile]):
    """Minimal concrete subclass for testing."""

    name = "dummy"

    def scrape_item(self, url: str) -> LinkedInProfile | None:
        # Simulate a successful scrape
        return LinkedInProfile(
            name="Test User",
            headline="Engineer at Acme",
            profile_url=url,
        )


class FailingDummyScraper(BaseScraper[LinkedInProfile]):
    """Scraper that always returns None to test error handling."""

    name = "failing"

    def scrape_item(self, url: str) -> LinkedInProfile | None:
        return None


class TestBaseScraperInit:
    """Tests for BaseScraper.__init__."""

    def test_default_delay_from_config(self):
        scraper = DummyScraper()
        assert scraper.delay > 0

    def test_custom_delay(self):
        scraper = DummyScraper(delay=5.0)
        assert scraper.delay == 5.0

    def test_custom_max_retries(self):
        scraper = DummyScraper(max_retries=5)
        assert scraper.max_retries == 5

    def test_extra_headers(self):
        scraper = DummyScraper(extra_headers={"X-Custom": "value"})
        assert scraper.extra_headers == {"X-Custom": "value"}

    def test_result_initialized(self):
        scraper = DummyScraper()
        assert scraper._result.total_requests == 0
        assert scraper._result.items == []
        assert scraper._result.errors == []


class TestBaseScraperScrapeBatch:
    """Tests for BaseScraper.scrape_batch."""

    def test_scrape_batch_all_success(self):
        scraper = DummyScraper(delay=0.01)
        urls = [
            "https://example.com/1",
            "https://example.com/2",
        ]
        result = scraper.scrape_batch(urls)
        assert len(result.items) == 2
        assert all(isinstance(p, LinkedInProfile) for p in result.items)
        assert result.total_requests == 2
        assert result.successful_requests == 2
        assert result.errors == []

    def test_scrape_batch_none_results(self):
        scraper = FailingDummyScraper(delay=0.01)
        urls = ["https://example.com/1"]
        result = scraper.scrape_batch(urls)
        assert result.items == []
        assert len(result.errors) == 1

    def test_reset_clears_result(self):
        scraper = DummyScraper(delay=0.01)
        scraper.scrape_batch(["https://example.com/1"])
        assert len(scraper._result.items) == 1
        scraper.reset()
        assert scraper._result.total_requests == 0
        assert scraper._result.items == []


class TestBaseScraperScrapeResult:
    """Tests for ScrapeResult model."""

    def test_success_rate_calculation(self):
        from src.models.base import ScrapeResult
        result = ScrapeResult[LinkedInProfile](
            total_requests=10,
            successful_requests=7,
        )
        assert result.success_rate == 0.7

    def test_success_rate_zero_requests(self):
        from src.models.base import ScrapeResult
        result = ScrapeResult[LinkedInProfile]()
        assert result.success_rate == 0.0

    def test_is_empty_true(self):
        from src.models.base import ScrapeResult
        result = ScrapeResult[LinkedInProfile]()
        assert result.is_empty is True

    def test_is_empty_false(self):
        from src.models.base import ScrapeResult
        result = ScrapeResult[LinkedInProfile](items=[LinkedInProfile(name="Test")])
        assert result.is_empty is False
