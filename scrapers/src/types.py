"""Shared TypedDict types used across the scrapers package."""

from __future__ import annotations

from typing import Literal

__all__ = ["RateLimitInfo", "ScrapeJob", "ScrapeStatus"]


class RateLimitInfo(dict):
    """Rate-limit configuration for a scraper."""

    requests_per_minute: int
    delay_seconds: float
    backoff_multiplier: float

    def __init__(
        self,
        requests_per_minute: int,
        delay_seconds: float,
        backoff_multiplier: float = 1.5,
    ) -> None:
        super().__init__(
            requests_per_minute=requests_per_minute,
            delay_seconds=delay_seconds,
            backoff_multiplier=backoff_multiplier,
        )
        self.requests_per_minute = requests_per_minute
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier


ScrapeStatus = Literal["pending", "running", "done", "failed"]


class ScrapeJob(dict):
    """Represents a queued scraping job."""

    id: str
    scraper: str
    args: dict
    status: ScrapeStatus
    created_at: str
    result_file: str | None
    error: str | None

    def __init__(
        self,
        id: str,
        scraper: str,
        args: dict,
        status: ScrapeStatus = "pending",
        created_at: str | None = None,
        result_file: str | None = None,
        error: str | None = None,
    ) -> None:
        import datetime

        super().__init__(
            id=id,
            scraper=scraper,
            args=args,
            status=status,
            created_at=created_at or datetime.datetime.utcnow().isoformat(),
            result_file=result_file,
            error=error,
        )
        self.id = id
        self.scraper = scraper
        self.args = args
        self.status = status
        self.created_at = created_at or datetime.datetime.utcnow().isoformat()
        self.result_file = result_file
        self.error = error
