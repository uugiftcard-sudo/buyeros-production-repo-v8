"""Unit tests for src/metrics_app.py and src/metrics.py."""

import pytest

from src.metrics import (
    active_scrapes,
    cache_hits,
    cache_misses,
    completed_jobs_total,
    queued_jobs,
    scrape_duration_seconds,
    scrape_requests_total,
)
from src.metrics_app import metrics_app


class TestMetrics:
    def test_scrape_requests_total_has_labels(self):
        """scrape_requests_total accepts scraper and status labels."""
        scrape_requests_total.labels(scraper="amazon", status="ok").inc()

    def test_scrape_duration_seconds_has_labels(self):
        """scrape_duration_seconds accepts scraper label."""
        # The context manager `.time()` returns a context manager
        with scrape_duration_seconds.labels(scraper="ebay").time():
            pass

    def test_active_scrapes_gauge(self):
        """active_scrapes gauge can be incremented and decremented."""
        active_scrapes.labels(scraper="amazon").inc()
        active_scrapes.labels(scraper="amazon").dec()

    def test_cache_hits_counter(self):
        """cache_hits counter accepts scraper label."""
        cache_hits.labels(scraper="amazon").inc()

    def test_cache_misses_counter(self):
        """cache_misses counter accepts scraper label."""
        cache_misses.labels(scraper="amazon").inc()

    def test_queued_jobs_gauge(self):
        """queued_jobs gauge works without labels."""
        queued_jobs.inc()
        queued_jobs.dec()

    def test_completed_jobs_total_counter(self):
        """completed_jobs_total accepts scraper and outcome labels."""
        completed_jobs_total.labels(scraper="amazon", outcome="success").inc()


class TestMetricsApp:
    def test_metrics_app_is_callable_wsgi(self):
        """metrics_app is a callable WSGI application."""
        assert callable(metrics_app)

    def test_metrics_app_is_asgi_app_with_mount(self):
        """metrics_app has a mount method (ASGI application interface)."""
        # prometheus_client.make_asgi_app() returns a Starlette ASGI app
        # which has a mount method for mounting sub-apps
        assert hasattr(metrics_app, "mount")
