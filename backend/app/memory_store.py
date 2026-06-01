"""BuyerOS durable memory facade with an in-memory fallback."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Sequence

import httpx

logger = logging.getLogger(__name__)


class MemoryStore:
    """Store operational memory in Supabase when configured, otherwise locally."""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None) -> None:
        self.supabase_url = (supabase_url or "").rstrip("/")
        self.supabase_key = supabase_key or ""
        self._items: list[dict[str, Any]] = []
        self._supabase_error_logged = False

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
            except Exception as exc:
                # Log the error once, then continue with in-memory fallback
                if not self._supabase_error_logged:
                    logger.warning("Supabase unavailable, using in-memory fallback: %s", exc)
                    self._supabase_error_logged = True
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
        if self.configured:
            try:
                return self._search_supabase(
                    namespace_prefix=namespace_prefix,
                    memory_key=memory_key,
                    query=query,
                    session_id=session_id,
                    source_provider=source_provider,
                    limit=limit,
                )
            except Exception as exc:
                if not self._supabase_error_logged:
                    logger.warning("Supabase search failed, using in-memory fallback: %s", exc)
                    self._supabase_error_logged = True
        
        # Fallback to in-memory search
        namespace_list = list(namespace_prefix)
        results = [
            item for item in self._items
            if item.get("namespace", [])[: len(namespace_list)] == namespace_list
        ]
        if memory_key:
            results = [r for r in results if r.get("memory_key") == memory_key]
        return results[:limit]

    def _save_supabase(self, item: dict[str, Any]) -> None:
        """Save to Supabase."""
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }
        response = httpx.post(
            f"{self.supabase_url}/rest/v1/memory",
            headers=headers,
            json=item,
            timeout=10.0,
        )
        response.raise_for_status()

    def _search_supabase(
        self,
        *,
        namespace_prefix: Iterable[str],
        memory_key: Optional[str] = None,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        source_provider: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Supabase."""
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }
        params = {
            "limit": str(limit),
        }
        if memory_key:
            params["memory_key"] = f"eq.{memory_key}"
        if session_id:
            params["session_id"] = f"eq.{session_id}"
        if source_provider:
            params["source_provider"] = f"eq.{source_provider}"
        
        response = httpx.get(
            f"{self.supabase_url}/rest/v1/memory",
            headers=headers,
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def get_memory(self, key: str) -> Any:
        """Get a single memory item by key."""
        for item in reversed(self._items):
            if item.get("memory_key") == key:
                return item.get("content")
        return None

    def set_memory(self, key: str, value: Any) -> None:
        """Set a memory item."""
        self._items.append({
            "namespace": ["api"],
            "memory_key": key,
            "content": value,
            "created_by": "api",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def delete_memory(self, key: str) -> None:
        """Delete a memory item by key."""
        self._items = [item for item in self._items if item.get("memory_key") != key]
