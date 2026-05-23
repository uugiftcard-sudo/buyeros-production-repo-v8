from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.context.context_hub import ContextHub
from app.context.provider_registry import BaseProviderAdapter, ProviderRegistry
from app.memory_store import MemoryStore


class FakeProvider(BaseProviderAdapter):
    def __init__(self, *, name: str, ok: bool, context_hub: ContextHub) -> None:
        super().__init__(context_hub=context_hub)
        self.name = name
        self.ok = ok

    def run(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "ok": self.ok,
            "reply": f"{self.name} {'handled' if self.ok else 'failed'}",
            "error": None if self.ok else "provider down",
        }


def test_coding_task_falls_back_from_claude_to_cursor() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    registry = ProviderRegistry()
    registry.register(FakeProvider(name="claude", ok=False, context_hub=hub))
    registry.register(FakeProvider(name="cursor", ok=True, context_hub=hub))
    registry.register(FakeProvider(name="openai", ok=True, context_hub=hub))

    result = registry.run(prompt="fix repo bug", session_id="fallback-code")

    assert result["provider"] == "cursor"
    assert result["fallback_exhausted"] is False
    assert result["fallback_chain"][:3] == ["claude", "cursor", "openai"]
    assert result["fallback_attempts"][0]["provider"] == "claude"
    assert hub.search_context(source_provider="claude", session_id="fallback-code")
    assert hub.search_context(source_provider="cursor", session_id="fallback-code")


def test_research_task_falls_back_from_perplexity_to_grok() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    registry = ProviderRegistry()
    registry.register(FakeProvider(name="perplexity", ok=False, context_hub=hub))
    registry.register(FakeProvider(name="grok", ok=True, context_hub=hub))
    registry.register(FakeProvider(name="openai", ok=True, context_hub=hub))

    result = registry.run(prompt="search latest news", session_id="fallback-research")

    assert result["provider"] == "grok"
    assert result["fallback_exhausted"] is False
    assert result["fallback_chain"][:3] == ["perplexity", "grok", "openai"]


def test_batch_task_falls_back_from_deepseek_to_minimax() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    registry = ProviderRegistry()
    registry.register(FakeProvider(name="deepseek", ok=False, context_hub=hub))
    registry.register(FakeProvider(name="minimax", ok=True, context_hub=hub))
    registry.register(FakeProvider(name="openai", ok=True, context_hub=hub))

    result = registry.run(prompt="batch process these rows", session_id="fallback-batch")

    assert result["provider"] == "minimax"
    assert result["fallback_chain"][:3] == ["deepseek", "minimax", "openai"]


def test_all_provider_failures_return_exhausted_result() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    registry = ProviderRegistry()
    registry.register(FakeProvider(name="claude", ok=False, context_hub=hub))
    registry.register(FakeProvider(name="cursor", ok=False, context_hub=hub))

    result = registry.run(prompt="fix code bug", session_id="fallback-none")

    assert result["ok"] is False
    assert result["fallback_exhausted"] is True
    assert len(result["fallback_attempts"]) == 2


def test_provider_exception_returns_structured_failure() -> None:
    class CrashingProvider(FakeProvider):
        def run(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
            raise RuntimeError("network exploded")

    memory = MemoryStore()
    hub = ContextHub(memory)
    registry = ProviderRegistry()
    registry.register(CrashingProvider(name="claude", ok=False, context_hub=hub))

    result = registry.run(prompt="fix code bug", session_id="fallback-crash")

    assert result["provider"] == "claude"
    assert result["ok"] is False
    assert result["fallback_exhausted"] is True
    assert result["fallback_attempts"][0]["error"] == "network exploded"
