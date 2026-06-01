"""Audit logging helpers for BuyerOS."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .memory_store import MemoryStore


class AuditLogger:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def log(self, *, action: str, actor: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "action": action,
            "actor": actor,
            "details": details or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.memory.save_memory(["buyeros", "audit"], action, payload, created_by=actor)
