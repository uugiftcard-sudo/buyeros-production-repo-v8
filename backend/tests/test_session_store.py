"""Tests for RedisSessionStore (Redis + in-memory fallback)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from app.runtime.session_store import RedisSessionStore


class TestRedisSessionStore:
    def test_save_and_get_round_trip(self) -> None:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.get.return_value = '{"user_id":"alice","message":"hello"}'

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis}):
            with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
                with patch("app.runtime.session_store.redis", mock_redis):
                    store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                    assert store.client is not None

                    store.save_state("session-1", {"user_id": "alice", "message": "hello"})
                    mock_client.setex.assert_called_once()
                    key_arg = mock_client.setex.call_args[0][0]
                    assert "session-1" in key_arg

                    state = store.get_state("session-1")
                    assert state["user_id"] == "alice"
                    assert state["message"] == "hello"

    def test_get_state_returns_none_when_no_client(self) -> None:
        mock_redis = MagicMock()
        mock_redis.Redis.from_url.side_effect = Exception("Connection refused")

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                assert store.client is None

                result = store.get_state("session-x")
                assert result is None

    def test_get_state_returns_none_when_key_missing(self) -> None:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                result = store.get_state("nonexistent-session")
                assert result is None

    def test_status_configured_and_healthy(self) -> None:
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                status = store.status()
                assert status["configured"] is True
                assert status["ok"] is True

    def test_status_configured_but_unhealthy(self) -> None:
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                # Connection refused → from_url raises → client set to None
                assert store.client is None
                status = store.status()
                assert status["configured"] is False
                assert status["ok"] is False

    def test_status_not_configured(self) -> None:
        store = RedisSessionStore(redis_url=None)
        assert store.client is None
        status = store.status()
        assert status["configured"] is False
        assert status["ok"] is False

    def test_save_state_skipped_when_no_session_id(self) -> None:
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                store.save_state(None, {"user_id": "bob"})
                mock_client.setex.assert_not_called()

    def test_save_state_skipped_when_no_client(self) -> None:
        mock_redis = MagicMock()
        mock_redis.Redis.from_url.side_effect = Exception("Redis down")

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                store.save_state("session-1", {"user_id": "bob"})
                mock_redis.Redis.from_url.return_value.setex.assert_not_called()

    def test_memory_hits_excluded_from_save(self) -> None:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.get.return_value = '{"user_id":"alice"}'

        mock_redis = MagicMock()
        mock_redis.Redis.from_url.return_value = mock_client

        with patch("app.runtime.session_store.redis.Redis", mock_redis.Redis):
            with patch("app.runtime.session_store.redis", mock_redis):
                store = RedisSessionStore(redis_url="redis://localhost:6379/0")
                store.save_state("session-1", {"user_id": "alice", "memory_hits": ["x", "y"]})
                # Verify memory_hits is not in the saved JSON string (3rd positional arg)
                mock_client.setex.assert_called_once()
                saved_json = mock_client.setex.call_args[0][2]
                assert "memory_hits" not in saved_json
