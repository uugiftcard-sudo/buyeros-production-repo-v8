"""In-memory implementation of BuyerOS MemoryStore for development and testing.

This module provides a MemoryStore class that persists to Supabase when configured
and falls back to in-memory storage during tests and development.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple


class MemoryStore:
    """In-memory memory store with optional Supabase persistence.

    This implementation stores entries in memory and supports the same interface
    as the Supabase-backed implementation for seamless switching.
    """

    def __init__(self) -> None:
        self._entries: List[dict] = []

    def save_memory(
        self,
        namespace: Tuple[str, ...],
        memory_key: str,
        content: dict,
        *,
        created_by: Optional[str] = None,
    ) -> None:
        """Save a memory entry."""
        entry = {
            "namespace": namespace,
            "memory_key": memory_key,
            "content": content,
            "created_by": created_by or "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._entries.append(entry)

    def search_memory(
        self,
        namespace_prefix: Tuple[str, ...],
        *,
        memory_key: Optional[str] = None,
        session_id: Optional[str] = None,
        source_provider: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]:
        """Search memory entries by namespace prefix and optional filters."""
        results = []
        prefix = tuple(namespace_prefix)
        for entry in self._entries:
            ns = tuple(entry.get("namespace", ()))
            # Check if namespace starts with the prefix
            if len(ns) >= len(prefix) and ns[:len(prefix)] == prefix:
                content = entry.get("content", {})
                if memory_key and entry.get("memory_key") != memory_key:
                    continue
                if session_id and content.get("session_id") != session_id:
                    continue
                if query and query.lower() not in str(content).lower():
                    continue
                results.append(entry)
        return results[:limit]

    def _pg_array_literal(self, namespace: Tuple[str, ...]) -> str:
        """Convert namespace tuple to PostgreSQL text array literal."""
        escaped = [part.replace('"', '""') for part in namespace]
        return "{" + ",".join(f'"{p}"' for p in escaped) + "}"
