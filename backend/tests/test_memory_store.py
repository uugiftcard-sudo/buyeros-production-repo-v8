from app.memory_store import MemoryStore


def test_memory_store_in_memory_save_and_search() -> None:
    memory = MemoryStore()
    memory.save_memory(["buyeros", "refunds"], "123", {"result": "ok"}, created_by="test")
    result = memory.search_memory(namespace_prefix=("buyeros", "refunds"), memory_key="123")
    assert len(result) == 1
    assert result[0]["content"]["result"] == "ok"


def test_pg_array_literal_uses_postgres_text_array_syntax() -> None:
    memory = MemoryStore()
    assert memory._pg_array_literal(("buyeros", "ai_context")) == '{"buyeros","ai_context"}'


def test_search_memory_filters_session_before_limit() -> None:
    memory = MemoryStore()
    memory.save_memory(
        ["buyeros", "ai_context", "claude"],
        "target",
        {"session_id": "target-session", "task_id": "target-task", "summary": "Refund 991 handled"},
        created_by="test",
    )
    for index in range(20):
        memory.save_memory(
            ["buyeros", "ai_context", "claude"],
            f"noise-{index}",
            {"session_id": "noise-session", "summary": f"newer noise {index}"},
            created_by="test",
        )

    result = memory.search_memory(
        namespace_prefix=("buyeros", "ai_context"),
        session_id="target-session",
        query="991",
        limit=1,
    )

    assert len(result) == 1
    assert result[0]["memory_key"] == "target"
