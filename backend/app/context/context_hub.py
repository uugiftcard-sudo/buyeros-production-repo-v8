"""Shared context API for BuyerOS agents and external AI clients."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from ..memory_store import MemoryStore


AI_CONTEXT_ROOT: Tuple[str, str] = ("buyeros", "ai_context")


class ContextHub:
    """Read/write facade over BuyerOS shared memory.

    Providers do not talk to each other directly. They exchange durable
    state through this hub, which persists to Supabase when configured and
    falls back to the local MemoryStore during tests and development.
    """

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory_store = memory_store

    def namespace_for(self, source_provider: str) -> List[str]:
        return [*AI_CONTEXT_ROOT, source_provider.lower().strip()]

    def write_context(
        self,
        *,
        source_provider: str,
        content: Dict[str, Any],
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        memory_key: Optional[str] = None,
        summary: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        provider = source_provider.lower().strip()
        key = memory_key or task_id or session_id or provider
        payload = {
            "source_provider": provider,
            "session_id": session_id,
            "task_id": task_id,
            "content": content,
            "summary": summary or self._summarize_content(content),
            "created_by": created_by or provider,
        }
        self.memory_store.save_memory(
            self.namespace_for(provider),
            key,
            payload,
            created_by=created_by or provider,
        )
        return {"memory_key": key, "namespace": self.namespace_for(provider), "content": payload}

    def search_context(
        self,
        *,
        query: Optional[str] = None,
        source_provider: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        namespace = tuple(self.namespace_for(source_provider)) if source_provider else AI_CONTEXT_ROOT
        entries = self.memory_store.search_memory(
            namespace_prefix=namespace,
            query=query,
            session_id=session_id,
            source_provider=source_provider,
            limit=limit,
        )
        return entries[:limit]

    def summarize_context(
        self,
        *,
        query: Optional[str] = None,
        source_provider: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        entries = self.search_context(
            query=query,
            source_provider=source_provider,
            session_id=session_id,
            limit=limit,
        )
        lines: List[str] = []
        for entry in entries:
            content = entry.get("content") or {}
            summary = content.get("summary")
            provider = content.get("source_provider") or "unknown"
            if summary:
                lines.append(f"{provider}: {summary}")
            else:
                lines.append(f"{provider}: {self._summarize_content(content)}")
        return {"count": len(entries), "summary": "\n".join(lines), "items": entries}

    def get_session(self, session_id: str, *, limit: int = 50) -> List[Dict[str, Any]]:
        return self.search_context(session_id=session_id, limit=limit)

    def _summarize_content(self, content: Dict[str, Any]) -> str:
        text = content.get("summary") or content.get("result") or content.get("reply") or content.get("text")
        if text is None:
            text = json.dumps(content, ensure_ascii=False, sort_keys=True)
        text = str(text).strip()
        return text[:240] + ("..." if len(text) > 240 else "")
