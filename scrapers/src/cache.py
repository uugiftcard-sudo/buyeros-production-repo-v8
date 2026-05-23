"""
Redis-backed cache layer for scrapers.

Skips gracefully when Redis is unavailable (log + pass-through).

Usage:
    from src.cache import Cache

    cache = Cache()
    cached = cache.get("amazon", "laptop")
    if cached is None:
        results = scraper.search("laptop")
        cache.set("amazon", "laptop", results, ttl=1800)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import redis

__all__ = ["Cache"]

_LOG = logging.getLogger(__name__)


class Cache:
    """
    Redis cache with SHA256 key normalisation and graceful degradation.

    Falls back to no-op when Redis is unavailable — callers always get
    ``None`` on miss and never raise.
    """

    def __init__(
        self,
        url: str | None = None,
        ttl: int = 3600,
    ) -> None:
        from src.config import settings

        self._url: str = url or getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        self._ttl: int = ttl
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis | None:
        """Lazily connect to Redis on first access."""
        if self._client is None:
            try:
                import redis as _redis

                self._client = _redis.from_url(self._url, socket_connect_timeout=2)
                # Smoke-test the connection
                self._client.ping()
                _LOG.info("[cache] Connected to Redis at %s", self._url)
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("[cache] Redis unavailable (%s) — caching disabled", exc)
                self._client = None
        return self._client

    @staticmethod
    def _key(scraper: str, lookup: str) -> str:
        """Normalise a cache key to a fixed-length SHA256 hex digest."""
        raw = f"{scraper}:{lookup}".encode()
        return hashlib.sha256(raw).hexdigest()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, scraper: str, lookup: str) -> list[dict[str, Any]] | None:
        """
        Retrieve cached results. Returns ``None`` on miss or if Redis is down.
        """
        client = self.client
        if client is None:
            return None

        try:
            raw = client.get(self._key(scraper, lookup))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("[cache] get failed: %s", exc)
            return None

    def set(
        self,
        scraper: str,
        lookup: str,
        value: list[dict[str, Any]],
        ttl: int | None = None,
    ) -> None:
        """Cache a list of result dicts. Silently no-ops on Redis failure."""
        client = self.client
        if client is None:
            return

        try:
            client.setex(
                self._key(scraper, lookup),
                ttl or self._ttl,
                json.dumps(value, default=str),
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("[cache] set failed: %s", exc)

    def invalidate(self, scraper: str, lookup: str) -> None:
        """Delete a specific cache entry. Silently no-ops on Redis failure."""
        client = self.client
        if client is None:
            return

        try:
            client.delete(self._key(scraper, lookup))
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("[cache] invalidate failed: %s", exc)

    def clear_scraper(self, scraper: str) -> int:
        """Delete all keys for a given scraper. Returns count deleted."""
        client = self.client
        if client is None:
            return 0

        try:
            pattern = f"{scraper}:*"
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("[cache] clear_scraper failed: %s", exc)
            return 0
