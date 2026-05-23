"""Tests for AIModelRouter (OpenRouter integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from app.ai_router import AIModelRouter


class TestAIModelRouter:
    def test_configured_true_when_api_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        router = AIModelRouter()
        assert router.api_key == "sk-or-v1-xxx"

    def test_route_no_key_returns_fallback_string(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        monkeypatch.setenv("OPENROUTER_MODEL_OPS", "openai/gpt-4o-mini")
        router = AIModelRouter()
        result = router.route(role="ops", prompt="process refund 123")
        assert result == "[AI fallback:ops] process refund 123"

    def test_route_ops_model_selected(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_OPS", "openai/gpt-4o-mini")
        monkeypatch.setenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Refund processed for 123."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            router = AIModelRouter()
            result = router.route(role="ops", prompt="process refund 123")
            assert result == "Refund processed for 123."
            call_json = mock_post.call_args[1]["json"]
            assert call_json["model"] == "openai/gpt-4o-mini"
            assert call_json["messages"][0]["role"] == "system"
            assert "ops" in call_json["messages"][0]["content"]

    def test_route_finance_model_selected(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_FINANCE", "anthropic/claude-3.5-sonnet")
        monkeypatch.setenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Profit this month: HKD 5000."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            router = AIModelRouter()
            result = router.route(role="finance", prompt="what is profit")
            assert result == "Profit this month: HKD 5000."
            call_json = mock_post.call_args[1]["json"]
            assert call_json["model"] == "anthropic/claude-3.5-sonnet"

    def test_route_timeout_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.Timeout("Connection timed out")

        with patch("requests.post", return_value=mock_response):
            router = AIModelRouter()
            with pytest.raises(requests.Timeout):
                router.route(role="supervisor", prompt="hello")

    def test_route_http_error_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("429 Rate limited")

        with patch("requests.post", return_value=mock_response):
            router = AIModelRouter()
            with pytest.raises(requests.HTTPError):
                router.route(role="supervisor", prompt="hello")

    def test_route_generic_prompt_uses_supervisor_model(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini")
        monkeypatch.setenv("OPENROUTER_MODEL_OPS", "openai/gpt-4o-mini")
        monkeypatch.setenv("OPENROUTER_MODEL_FINANCE", "openai/gpt-4o-mini")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Handled."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            router = AIModelRouter()
            router.route(role="unknown_role", prompt="generic message")
            call_json = mock_post.call_args[1]["json"]
            assert call_json["model"] == "openai/gpt-4o-mini"


import pytest  # noqa: E402
