from app.context.context_hub import ContextHub
from app.context.provider_registry import ProviderRegistry
from app.context.adapters.claude import ClaudeProviderAdapter
from app.context.adapters.cursor import CursorProviderAdapter
from app.context.adapters.openclaw import OpenClawProviderAdapter
from app.memory_store import MemoryStore


def test_context_write_and_cross_provider_search() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)

    hub.write_context(
        source_provider="claude",
        session_id="session-1",
        task_id="task-1",
        content={"text": "Refund 991 was handled"},
        summary="Refund 991 handled",
    )

    result = hub.search_context(query="991", source_provider="claude", limit=5)
    assert len(result) == 1
    assert result[0]["content"]["source_provider"] == "claude"

    session_result = hub.get_session("session-1")
    assert session_result


def test_provider_registry_routes_coding_and_writes_context() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    registry = ProviderRegistry()
    registry.register(ClaudeProviderAdapter(context_hub=hub))
    registry.register(CursorProviderAdapter(context_hub=hub))

    result = registry.run(prompt="fix this code bug", session_id="dev")

    assert result["ok"] is False
    assert result["fallback_exhausted"] is True
    stored = hub.search_context(source_provider="claude", session_id="dev")
    assert stored


def test_context_session_search_filters_before_limit() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    hub.write_context(
        source_provider="claude",
        session_id="session-target",
        task_id="task-target",
        content={"text": "退款 991 已完成"},
        summary="退款 991 已完成",
    )
    for index in range(20):
        hub.write_context(
            source_provider="claude",
            session_id="other-session",
            task_id=f"noise-{index}",
            content={"text": f"noise {index}"},
            summary=f"noise {index}",
        )

    result = hub.search_context(query="991", session_id="session-target", limit=1)

    assert len(result) == 1
    assert result[0]["content"]["session_id"] == "session-target"


def test_openclaw_adapter_writes_shared_context() -> None:
    memory = MemoryStore()
    hub = ContextHub(memory)
    adapter = OpenClawProviderAdapter(context_hub=hub)

    result = adapter.run("orchestrate tool task", context=[])
    adapter.write_context(result, session_id="ops", task_id="openclaw-1")

    stored = hub.search_context(source_provider="openclaw", session_id="ops")
    assert stored
    assert stored[0]["content"]["source_provider"] == "openclaw"
