"""Tests for ProviderRegistry and provider adapters."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.context.adapters.cursor import CursorProviderAdapter
from app.context.adapters.perplexity import PerplexityProviderAdapter
from app.context.adapters.openclaw import OpenClawProviderAdapter
from app.context.adapters.hermes import HermesProviderAdapter
from app.context.adapters.minimax import MiniMaxProviderAdapter
from app.context.context_hub import ContextHub
from app.context.provider_registry import BaseProviderAdapter, ProviderRegistry
from app.context.adapters.claude import ClaudeProviderAdapter
from app.context.adapters.openai import OpenAIProviderAdapter
from app.context.adapters.deepseek import DeepSeekProviderAdapter
from app.context.adapters.openrouter import OpenRouterProviderAdapter
from app.memory_store import MemoryStore


class TestBaseProviderAdapter:
    def test_disabled_provider_returns_disabled_message(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = BaseProviderAdapter(context_hub=hub, enabled=False)
        result = adapter.run("test prompt")
        assert result["ok"] is False
        assert "not configured yet" in result["reply"]

    def test_run_via_openrouter_no_key_returns_none(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = BaseProviderAdapter(context_hub=hub, enabled=True)
        result = adapter._run_via_openrouter("test prompt")
        assert result is None

    def test_run_without_provider_key_returns_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = BaseProviderAdapter(context_hub=hub, enabled=True)
        result = adapter.run("test prompt")
        assert result["ok"] is False
        assert result["status"] == "not_configured"
        assert result["error"] == "provider_not_configured"

    def test_run_via_openrouter_success(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_BASE", "openai/gpt-4o-mini")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = BaseProviderAdapter(context_hub=hub, enabled=True, model_env="OPENROUTER_MODEL_BASE")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Claude response here."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = adapter._run_via_openrouter("test prompt", context=[])
            assert result is not None
            assert result["ok"] is True
            assert result["via"] == "openrouter"
            assert result["reply"] == "Claude response here."

    def test_run_via_openrouter_error_returns_failure_dict(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_BASE", "openai/gpt-4o-mini")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = BaseProviderAdapter(context_hub=hub, enabled=True, model_env="OPENROUTER_MODEL_BASE")

        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("429 Rate limited")

        with patch("requests.post", return_value=mock_response):
            result = adapter._run_via_openrouter("test prompt")
            assert result["ok"] is False
            assert "failed" in result["reply"].lower()
            assert "error" in result

    def test_write_context_delegates_to_hub(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = BaseProviderAdapter(context_hub=hub, enabled=True)
        adapter.name = "test_provider"
        result = adapter.write_context(
            {"reply": "test response"},
            session_id="sess-1",
            task_id="task-1",
        )
        assert "memory_key" in result
        assert "namespace" in result
        stored = hub.search_context(source_provider="test_provider", session_id="sess-1")
        assert len(stored) >= 1


class TestProviderRegistry:
    def test_register_and_get(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        adapter = ClaudeProviderAdapter(context_hub=hub)
        registry.register(adapter)
        retrieved = registry.get("claude")
        assert retrieved.name == "claude"

    def test_get_unknown_provider_raises_keyerror(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(KeyError) as exc_info:
            registry.get("unknown")
        assert "unknown" in str(exc_info.value)

    def test_has_provider(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(ClaudeProviderAdapter(context_hub=hub))
        assert registry.has_provider("claude") is True
        assert registry.has_provider("openai") is False

    def test_names_returns_sorted_list(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(OpenAIProviderAdapter(context_hub=hub))
        registry.register(ClaudeProviderAdapter(context_hub=hub))
        names = registry.names()
        assert names == sorted(names)
        assert "claude" in names
        assert "openai" in names

    def test_status_returns_provider_details(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_OPENAI", "openai/gpt-4o-mini")
        monkeypatch.setenv("OPENROUTER_MODEL_CLAUDE", "anthropic/claude-3.5-sonnet")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(ClaudeProviderAdapter(context_hub=hub))
        registry.register(OpenAIProviderAdapter(context_hub=hub))

        status = registry.status()
        assert isinstance(status, list)
        names = [p["name"] for p in status]
        assert "claude" in names
        assert "openai" in names
        for p in status:
            assert "openrouter_configured" in p
            assert "enabled" in p
            assert "model" in p

    def test_choose_provider_respects_preferred(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(OpenAIProviderAdapter(context_hub=hub))
        registry.register(ClaudeProviderAdapter(context_hub=hub))

        chosen = registry.choose_provider("process refund", preferred="claude")
        assert chosen == "claude"

    def test_choose_provider_code_keyword_routes_to_claude(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(ClaudeProviderAdapter(context_hub=hub))
        registry.register(OpenAIProviderAdapter(context_hub=hub))

        for prompt in ["fix code bug", "how to code this", "repo review", "claude analysis"]:
            chosen = registry.choose_provider(prompt)
            assert chosen == "claude", f"Failed for prompt: {prompt}"

    def test_choose_provider_cursor_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        # Only cursor registered, not claude
        registry.register(CursorProviderAdapter(context_hub=hub))

        chosen = registry.choose_provider("fix code bug")
        assert chosen == "cursor"

    def test_choose_provider_research_keyword(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(OpenAIProviderAdapter(context_hub=hub))
        registry.register(PerplexityProviderAdapter(context_hub=hub))

        chosen = registry.choose_provider("search latest news")
        assert chosen == "perplexity"

    def test_choose_provider_batch_keyword(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(DeepSeekProviderAdapter(context_hub=hub))
        registry.register(MiniMaxProviderAdapter(context_hub=hub))

        for prompt in ["batch process these", "cheap large scale", "大量處理"]:
            chosen = registry.choose_provider(prompt)
            assert chosen == "deepseek", f"Failed for: {prompt}"

    def test_choose_provider_openclaw_hermes(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(OpenClawProviderAdapter(context_hub=hub))
        registry.register(HermesProviderAdapter(context_hub=hub))

        chosen = registry.choose_provider("orchestrate tools")
        assert chosen == "openclaw"

    def test_choose_provider_fallback_to_openai(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(OpenAIProviderAdapter(context_hub=hub))
        registry.register(ClaudeProviderAdapter(context_hub=hub))

        chosen = registry.choose_provider("hello world")
        assert chosen == "openai"

    def test_choose_provider_fallback_to_first_registered(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        # Only deepseek registered
        registry.register(DeepSeekProviderAdapter(context_hub=hub))

        chosen = registry.choose_provider("hello world")
        assert chosen == "deepseek"

    def test_run_delegates_to_chosen_provider(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(ClaudeProviderAdapter(context_hub=hub))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Refunded 123."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = registry.run(prompt="refund transaction 123", session_id="sess-1")
            assert result["provider"] == "claude"
            # Context should be written
            stored = hub.search_context(source_provider="claude", session_id="sess-1")
            assert len(stored) >= 1

    def test_run_writes_context_on_error(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(ClaudeProviderAdapter(context_hub=hub))

        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("Network error")

        with patch("requests.post", return_value=mock_response):
            result = registry.run(prompt="hello", session_id="sess-2")
            assert result["ok"] is False
            # Still writes context even on error
            stored = hub.search_context(source_provider="claude", session_id="sess-2")
            assert len(stored) >= 1


# ── Individual provider adapter smoke tests ──────────────────────────────────

class TestProviderAdapterSmoke:
    """Smoke tests: each adapter can be instantiated and run without errors."""

    def test_claude_adapter_runs(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = ClaudeProviderAdapter(context_hub=hub)
        assert adapter.name == "claude"
        result = adapter.run("hello")
        assert "reply" in result

    def test_openai_adapter_runs(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = OpenAIProviderAdapter(context_hub=hub)
        assert adapter.name == "openai"
        result = adapter.run("hello")
        assert "reply" in result

    def test_deepseek_adapter_runs(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = DeepSeekProviderAdapter(context_hub=hub)
        assert adapter.name == "deepseek"
        result = adapter.run("hello")
        assert "reply" in result

    def test_openrouter_adapter_runs(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = OpenRouterProviderAdapter(context_hub=hub)
        assert adapter.name == "openrouter"
        # Mock the live API call by patching the module-level requests reference
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Handled"}}]
        }
        mock_response.raise_for_status = MagicMock()
        with patch("app.context.adapters.openrouter.requests.post", return_value=mock_response):
            result = adapter.run("hello")
        assert "reply" in result

    def test_openrouter_adapter_gracefully_handles_http_error(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        adapter = OpenRouterProviderAdapter(context_hub=hub)

        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("429")
        with patch("app.context.adapters.openrouter.requests.post", return_value=mock_response):
            result = adapter.run("hello")

        assert result["ok"] is False
        assert result["provider"] == "openrouter"
        assert "failed" in result["reply"]
