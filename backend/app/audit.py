"""Audit logging backed by BuyerOS memory."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .memory_store import MemoryStore


class AuditLogger:
    """Write lightweight audit records to shared memory."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory_store = memory_store

    def log(self, *, action: str, actor: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.memory_store.save_memory(
            ["buyeros", "audit"],
            action,
            {"action": action, "actor": actor, "details": details or {}},
            created_by="audit",
        )

