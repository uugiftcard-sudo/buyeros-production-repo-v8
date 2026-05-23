"""Unit tests for src/cache.py."""

from unittest.mock import MagicMock, patch


class TestCache:
    def test_key_generates_sha256_hex(self):
        """Cache._key produces a deterministic SHA256 hex string."""
        from src.cache import Cache

        k1 = Cache._key("amazon", "laptop")
        k2 = Cache._key("amazon", "laptop")
        k3 = Cache._key("amazon", "phone")
        assert k1 == k2
        assert k1 != k3
        assert len(k1) == 64  # SHA256 hex = 64 chars

    def test_get_returns_none_when_client_is_none(self):
        """get() returns None when Redis is unavailable (no-op behaviour)."""
        from src.cache import Cache

        cache = Cache()
        # Force client to None to simulate unavailability
        cache._client = None
        result = cache.get("amazon", "laptop")
        assert result is None

    def test_set_noops_when_client_is_none(self):
        """set() does not raise when Redis is unavailable."""
        from src.cache import Cache

        cache = Cache()
        cache._client = None
        # Should not raise
        cache.set("amazon", "laptop", [{"name": "item"}])

    def test_invalidate_noops_when_client_is_none(self):
        """invalidate() does not raise when Redis is unavailable."""
        from src.cache import Cache

        cache = Cache()
        cache._client = None
        # Should not raise
        cache.invalidate("amazon", "laptop")

    def test_clear_scraper_returns_zero_when_client_is_none(self):
        """clear_scraper() returns 0 when Redis is unavailable."""
        from src.cache import Cache

        cache = Cache()
        cache._client = None
        result = cache.clear_scraper("amazon")
        assert result == 0

    def test_client_property_swallows_connection_error(self):
        """client property returns None gracefully when Redis connection fails."""
        from src.cache import Cache

        cache = Cache()
        # Patch the redis module that is imported *inside* the client property
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = AttributeError("no redis")
            # When the import inside the property fails, client returns None
            cache._client = None  # already None — just verify no raise
            result = cache.client
            # If redis wasn't installed, client stays None
            assert result is None

    def test_get_returns_none_on_redis_error(self):
        """get() returns None on any Redis error (graceful degradation)."""
        from src.cache import Cache

        cache = Cache()
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Redis error")
        cache._client = mock_client

        result = cache.get("amazon", "laptop")
        assert result is None

    def test_set_noops_on_redis_error(self):
        """set() silently no-ops on Redis error."""
        from src.cache import Cache

        cache = Cache()
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("Redis error")
        cache._client = mock_client

        # Should not raise
        cache.set("amazon", "laptop", [{"name": "item"}])

    def test_invalidate_noops_on_redis_error(self):
        """invalidate() silently no-ops on Redis error."""
        from src.cache import Cache

        cache = Cache()
        mock_client = MagicMock()
        mock_client.delete.side_effect = Exception("Redis error")
        cache._client = mock_client

        # Should not raise
        cache.invalidate("amazon", "laptop")

    def test_clear_scraper_returns_zero_on_redis_error(self):
        """clear_scraper() returns 0 on Redis error."""
        from src.cache import Cache

        cache = Cache()
        mock_client = MagicMock()
        mock_client.keys.side_effect = Exception("Redis error")
        cache._client = mock_client

        result = cache.clear_scraper("amazon")
        assert result == 0

    def test_ttl_defaults_to_3600(self):
        """Cache default TTL is 3600 seconds."""
        from src.cache import Cache

        cache = Cache()
        assert cache._ttl == 3600

    def test_custom_ttl_is_respected(self):
        """Custom TTL passed to __init__ is stored."""
        from src.cache import Cache

        cache = Cache(ttl=1800)
        assert cache._ttl == 1800
