"""
Base scraper class — shared retry, rate-limiting, UA rotation, error handling.

Subclass this to implement a platform-specific scraper.
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import requests
from tenacity import Retrying, stop_after_attempt, wait_exponential, before_sleep_log

from src.config import get_delay, get_max_retries, get_user_agents
from src.models.base import BaseScrapedItem, HTTPError, ScrapeResult

if TYPE_CHECKING:
    from pydantic import BaseModel

T = TypeVar("T", bound=BaseScrapedItem)

_LOG = logging.getLogger(__name__)


class BaseScraper(ABC, Generic[T]):
    """
    Abstract base class for all platform scrapers.

    Provides:
    - User-Agent rotation
    - Retry with exponential backoff
    - Per-request delay / rate limiting
    - Error collection (continues on individual item failure)
    - Typed result model

    Subclasses must implement `scrape_item(url: str) -> T`.
    """

    name: str = "base"

    def __init__(
        self,
        delay: float | None = None,
        max_retries: int | None = None,
        extra_headers: dict[str, str] | None = None,
        proxies: dict[str, str] | None = None,
    ) -> None:
        self.delay = delay if delay is not None else get_delay(self.name)
        self.max_retries = max_retries or get_max_retries()
        self.extra_headers = extra_headers or {}
        self.proxies = proxies
        self._result = ScrapeResult[T]()

    # ── User-Agent rotation ─────────────────────────────────────

    def _random_ua(self) -> str:
        """Return a random User-Agent from the pool."""
        return random.choice(get_user_agents())

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers with random UA."""
        base = {
            "User-Agent": self._random_ua(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        base.update(self.extra_headers)
        if extra:
            base.update(extra)
        return base

    # ── HTTP ────────────────────────────────────────────────────

    def _get(self, url: str, **kwargs: Any) -> requests.Response | None:
        """
        Perform a GET with retry + backoff, returning the response or None.
        """
        for attempt in Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            before_sleep=before_sleep_log(_LOG, logging.WARNING),
            reraise=True,
        ):
            with attempt:
                try:
                    resp = requests.get(
                        url,
                        headers=self._headers(),
                        timeout=15,
                        proxies=self.proxies,
                        **kwargs,
                    )
                    self._result.total_requests += 1
                    if resp.ok:
                        self._result.successful_requests += 1
                        return resp
                    if resp.status_code in (403, 429, 499, 999):
                        backoff = random.uniform(5, 15)
                        _LOG.warning(f"Blocked ({resp.status_code}), sleeping {backoff:.0f}s")
                        time.sleep(backoff)
                        raise requests.RequestException(f"Blocked: {resp.status_code}")
                    resp.raise_for_status()
                    self._result.successful_requests += 1
                    return resp
                except requests.RequestException:
                    raise
        return None

    def _post(self, url: str, **kwargs: Any) -> requests.Response | None:
        """Perform a POST with retry + backoff."""
        for attempt in Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            before_sleep=before_sleep_log(_LOG, logging.WARNING),
            reraise=True,
        ):
            with attempt:
                try:
                    resp = requests.post(
                        url,
                        headers=self._headers(),
                        timeout=15,
                        proxies=self.proxies,
                        **kwargs,
                    )
                    self._result.total_requests += 1
                    if resp.ok:
                        self._result.successful_requests += 1
                        return resp
                    resp.raise_for_status()
                    self._result.successful_requests += 1
                    return resp
                except requests.RequestException:
                    raise
        return None

    # ── Rate limiting ────────────────────────────────────────────

    def _wait(self) -> None:
        """Apply per-request delay with random jitter."""
        jitter = random.uniform(-0.5, 0.5)
        sleep = max(0.5, self.delay + jitter)
        time.sleep(sleep)

    # ── Abstract interface ──────────────────────────────────────

    @abstractmethod
    def scrape_item(self, url: str) -> T | None:
        """
        Scrape a single item from `url`. Return the model or None on failure.
        """
        ...

    # ── Batch interface ─────────────────────────────────────────

    def scrape_batch(self, urls: list[str]) -> ScrapeResult[T]:
        """
        Scrape multiple URLs sequentially with rate limiting.

        Errors are collected per-item but do not stop the batch.
        """
        for url in urls:
            self._wait()
            self._result.total_requests += 1
            try:
                item = self.scrape_item(url)
                if item is not None:
                    self._result.successful_requests += 1
                    self._result.items.append(item)
                else:
                    self._result.errors.append(
                        HTTPError(url=url, error_message="scrape_item returned None")
                    )
            except Exception as exc:  # noqa: BLE001
                _LOG.error(f"[{self.name}] Failed to scrape {url}: {exc}")
                self._result.errors.append(
                    HTTPError(url=url, error_message=str(exc))
                )
        return self._result

    def scrape(self, *args: Any, **kwargs: Any) -> list[T]:
        """
        Convenience: run the scraper and return just the items list.

        Subclasses may override this for custom logic (e.g. keyword search).
        """
        raise NotImplementedError("Override in subclass or call scrape_batch()")

    @property
    def result(self) -> ScrapeResult[T]:
        """Return the current ScrapeResult with all collected items and errors."""
        return self._result

    def reset(self) -> None:
        """Reset the internal result collector for a fresh run."""
        self._result = ScrapeResult[T]()
