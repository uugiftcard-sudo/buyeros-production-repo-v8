"""
Async base scraper — asynchronous, concurrent sibling of BaseScraper.

Use this when scraping many URLs concurrently for speed.
For sequential scraping with simpler semantics, use BaseScraper instead.

Example:
    class MyAsyncScraper(AsyncBaseScraper[MyItem]):
        name = "my_scraper"

        async def scrape_item(self, url: str, client: httpx.AsyncClient) -> MyItem | None:
            resp = await client.get(url)
            return MyItem.model_validate_json(resp.text)

    scraper = MyAsyncScraper()
    result = await scraper.scrape_batch(urls)
"""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

import httpx

from src.config import get_delay, get_max_retries, get_user_agents
from src.metrics import (
    active_scrapes,
    scrape_duration_seconds,
    scrape_requests_total,
)
from src.models.base import HTTPError, ScrapeResult

if TYPE_CHECKING:
    from pydantic import BaseModel

T = TypeVar("T", bound="BaseModel")

_LOG = logging.getLogger(__name__)


class AsyncBaseScraper(ABC, Generic[T]):
    """
    Abstract async base class for concurrent scraping.

    Provides:
    - User-Agent rotation (random per request)
    - Exponential-backoff retry via httpx
    - Configurable concurrency limit (semaphore)
    - Prometheus metrics integration
    - Per-request rate-limiting delay

    Subclasses must implement ``scrape_item(url, client)``.
    """

    name: str = "async_base"

    def __init__(
        self,
        delay: float | None = None,
        max_retries: int | None = None,
        max_concurrency: int = 5,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.delay = delay if delay is not None else get_delay(self.name)
        self.max_retries = max_retries or get_max_retries()
        self.max_concurrency = max_concurrency
        self.extra_headers = extra_headers or {}
        self._result = ScrapeResult[T]()

    # ── User-Agent ─────────────────────────────────────────────────────────────

    def _random_ua(self) -> str:
        return random.choice(get_user_agents())

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        base = {
            "User-Agent": self._random_ua(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        base.update(self.extra_headers)
        if extra:
            base.update(extra)
        return base

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def scrape_item(self, url: str, client: httpx.AsyncClient) -> T | None:
        """
        Fetch and parse a single URL. Return the parsed model or None on failure.

        Use ``client`` for HTTP operations — it is pre-configured with retry and headers.
        """
        ...

    # ── Core async loop ──────────────────────────────────────────────────────

    async def _fetch_one(
        self,
        url: str,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Run a single fetch inside the concurrency semaphore."""
        async with semaphore:
            active_scrapes.labels(scraper=self.name).inc()

            with scrape_duration_seconds.labels(scraper=self.name).time():
                try:
                    item = await self.scrape_item(url, client)
                    if item is not None:
                        self._result.items.append(item)
                        self._result.successful_requests += 1
                        scrape_requests_total.labels(scraper=self.name, status="ok").inc()
                    else:
                        self._result.errors.append(
                            HTTPError(url=url, error_message="scrape_item returned None")
                        )
                        scrape_requests_total.labels(scraper=self.name, status="error").inc()
                except Exception as exc:  # noqa: BLE001
                    _LOG.error("[%s] Failed %s: %s", self.name, url, exc)
                    self._result.errors.append(HTTPError(url=url, error_message=str(exc)))
                    scrape_requests_total.labels(scraper=self.name, status="error").inc()

            self._result.total_requests += 1
            active_scrapes.labels(scraper=self.name).dec()

            # Rate-limit between requests (outside semaphore to not block other tasks)
            await asyncio.sleep(self.delay)

    async def scrape_batch(self, urls: list[str]) -> ScrapeResult[T]:
        """
        Scrape multiple URLs concurrently.

        Uses a semaphore to cap concurrency. Errors are collected per-item
        and do not stop the batch.
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)

        timeout = httpx.Timeout(15.0, connect=5.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=self._headers(),
            follow_redirects=True,
        ) as client:
            tasks = [self._fetch_one(url, client, semaphore) for url in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

        return self._result

    # ── Convenience ──────────────────────────────────────────────────────────

    @property
    def result(self) -> ScrapeResult[T]:
        """Return the current ScrapeResult."""
        return self._result

    def reset(self) -> None:
        """Clear results for a fresh run."""
        self._result = ScrapeResult[T]()
