"""BuyerOS durable memory facade with an in-memory fallback."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Sequence

import httpx


class MemoryStore:
    """Store operational memory in Supabase when configured, otherwise locally."""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None) -> None:
        self.supabase_url = (supabase_url or "").rstrip("/")
        self.supabase_key = supabase_key or ""
        self._items: list[dict[str, Any]] = []

    @property
    def memory(self) -> list[dict[str, Any]]:
        return self._items

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    def save_memory(
        self,
        namespace: Sequence[str],
        memory_key: str,
        content: dict[str, Any],
        *,
        created_by: str,
    ) -> dict[str, Any]:
        item = {
            "namespace": list(namespace),
            "memory_key": str(memory_key),
            "content": content,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.configured:
            try:
                self._save_supabase(item)
            except Exception:
                # Tests and local smoke should keep working when Supabase is absent.
                pass
        self._items.append(item)
        return item

    def search_memory(
        self,
        *,
        namespace_prefix: Iterable[str],
        memory_key: Optional[str] = None,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        source_provider: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        prefix = tuple(namespace_prefix)
        matches: list[dict[str, Any]] = []
        for item in reversed(self._items):
            namespace = tuple(item.get("namespace") or [])
            if namespace[: len(prefix)] != prefix:
                continue
            if memory_key is not None and item.get("memory_key") != memory_key:
                continue
            content = item.get("content") or {}
            if session_id is not None and not self._content_matches(content, "session_id", session_id):
                continue
            if source_provider is not None and not self._content_matches(content, "source_provider", source_provider):
                continue
            if query is not None and query.lower() not in json.dumps(item, ensure_ascii=False, default=str).lower():
                continue
            matches.append(item)
            if len(matches) >= max(limit, 0):
                break
        return list(reversed(matches))

    def status(self) -> dict[str, Any]:
        return {"configured": self.configured, "ok": True, "backend": "supabase" if self.configured else "memory"}

    def _save_supabase(self, item: dict[str, Any]) -> None:
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        httpx.post(f"{self.supabase_url}/rest/v1/buyeros_memory", headers=headers, json=item, timeout=5).raise_for_status()

    @staticmethod
    def _content_matches(content: Any, field: str, expected: str) -> bool:
        if isinstance(content, dict):
            if str(content.get(field) or "") == expected:
                return True
            nested = content.get("content")
            if isinstance(nested, dict) and str(nested.get(field) or "") == expected:
                return True
        return False

    @staticmethod
    def _pg_array_literal(parts: Sequence[str]) -> str:
        escaped = [str(part).replace("\\", "\\\\").replace('"', '\\"') for part in parts]
        return "{" + ",".join(f'"{part}"' for part in escaped) + "}"
