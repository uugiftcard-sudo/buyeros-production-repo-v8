from app.audit import AuditLogger
from app.memory_store import MemoryStore


def test_audit_logger_writes_to_audit_namespace() -> None:
    memory = MemoryStore()
    audit = AuditLogger(memory)

    audit.log(action="agents.run", actor="tester", details={"ok": True})

    entries = memory.search_memory(namespace_prefix=("buyeros", "audit"), memory_key="agents.run")
    assert entries
    assert entries[0]["content"]["actor"] == "tester"
