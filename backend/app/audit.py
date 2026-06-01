"""Audit logging for BuyerOS operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from app.memory_store import MemoryStore


class AuditLogger:
    """Audit logger for tracking operations with optional memory store."""

    def __init__(self, memory_store: Optional["MemoryStore"] = None) -> None:
        self._logs: list = []
        self._memory: Optional["MemoryStore"] = memory_store

    def log(self, action: str = "", **kwargs: Any) -> None:
        """Log an audit event."""
        entry = {
            "event": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self._logs.append(entry)
        # Also persist to memory store if available
        if self._memory:
            self._memory.save_memory(
                ("buyeros", "audit"),
                action,
                entry,
                created_by=kwargs.get("actor", "system"),
            )

    def get_logs(self, event: Optional[str] = None) -> list:
        """Get audit logs, optionally filtered by event type."""
        if event:
            return [log for log in self._logs if log.get("event") == event]
        return self._logs
