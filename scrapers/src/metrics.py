"""
Prometheus metrics for the scrapers package.

Exposed at: GET /metrics  (via prometheus_client.make_asgi_app)
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "scrape_requests_total",
    "scrape_duration_seconds",
    "active_scrapes",
    "cache_hits",
    "cache_misses",
]

# ── Request counters ────────────────────────────────────────────────────────────

scrape_requests_total = Counter(
    "scraper_requests_total",
    "Total scrape requests by scraper and status",
    ["scraper", "status"],  # status: ok | error | blocked | cached
)

# ── Duration histograms ─────────────────────────────────────────────────────────

scrape_duration_seconds = Histogram(
    "scraper_duration_seconds",
    "Scrape duration in seconds",
    ["scraper"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# ── Active scrape gauge ────────────────────────────────────────────────────────

active_scrapes = Gauge(
    "scraper_active_scrapes",
    "Number of currently-running scrape operations",
    ["scraper"],
)

# ── Cache metrics ──────────────────────────────────────────────────────────────

cache_hits = Counter(
    "scraper_cache_hits_total",
    "Total cache hits",
    ["scraper"],
)

cache_misses = Counter(
    "scraper_cache_misses_total",
    "Total cache misses",
    ["scraper"],
)

# ── Job queue metrics ──────────────────────────────────────────────────────────

queued_jobs = Gauge(
    "scraper_queued_jobs",
    "Number of pending jobs in the queue",
)

completed_jobs_total = Counter(
    "scraper_completed_jobs_total",
    "Total completed jobs",
    ["scraper", "outcome"],  # outcome: success | failed
)
