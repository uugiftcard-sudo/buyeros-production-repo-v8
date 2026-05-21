from app.memory_store import MemoryStore


def test_memory_store_in_memory_save_and_search() -> None:
    memory = MemoryStore()
    memory.save_memory(["buyeros", "refunds"], "123", {"result": "ok"}, created_by="test")
    result = memory.search_memory(namespace_prefix=("buyeros", "refunds"), memory_key="123")
    assert len(result) == 1
    assert result[0]["content"]["result"] == "ok"
