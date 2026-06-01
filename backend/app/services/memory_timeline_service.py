"""Memory timeline queries for BuyerOS shared state."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..memory_store import MemoryStore
from .canonical_workspace import normalize_workspace


class MemoryTimelineService:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    @staticmethod
    def normalize_project_id(project_id: Optional[str]) -> Optional[str]:
        raw = (project_id or "").strip()
        if not raw:
            return None
        return normalize_workspace(raw)

    def timeline(
        self,
        *,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        # Pull from a small set of namespaces that matter operationally.
        namespaces: List[Tuple[str, ...]] = [
            ("buyeros", "audit"),
            ("buyeros", "tasks"),
            ("buyeros", "task_runs"),
            ("buyeros", "dispatch_plans"),
            ("buyeros", "subtasks"),
            ("buyeros", "routing"),
            ("buyeros", "run_all"),
            ("buyeros", "ai_context"),
            ("buyeros", "projects"),
            ("buyeros", "reports"),
            ("buyeros", "refunds"),
            ("buyeros", "orders"),
            ("buyeros", "buyers"),
            ("buyeros", "promo"),
            ("buyeros", "alerts"),
            ("buyeros", "ocr_entries"),
            ("buyeros", "retries"),
            ("buyeros", "approvals"),
            ("buyeros", "reconciliation"),
            ("buyeros", "close_cycles"),
        ]
        candidates: List[Dict[str, Any]] = []
        # Fetch more than limit because we will filter and merge.
        per_ns = max(20, min(200, limit * 2))
        for prefix in namespaces:
            candidates.extend(
                self.memory.search_memory(
                    namespace_prefix=prefix,
                    query=query,
                    session_id=session_id,
                    limit=per_ns,
                )
            )
        normalized_project_id = self.normalize_project_id(project_id)
        if normalized_project_id:
            filtered: List[Dict[str, Any]] = []
            for item in candidates:
                content = item.get("content") or {}
                payload = content.get("payload") if isinstance(content, dict) else None
                if isinstance(payload, dict) and self.normalize_project_id(str(payload.get("project") or "")) == normalized_project_id:
                    filtered.append(item)
                    continue
                if self.normalize_project_id(str(content.get("project_id") or "")) == normalized_project_id:
                    filtered.append(item)
                    continue
                if self.normalize_project_id(str(content.get("project") or "")) == normalized_project_id:
                    filtered.append(item)
                    continue
                if content.get("task_id") and isinstance(payload, dict) and self.normalize_project_id(str(payload.get("project") or "")) == normalized_project_id:
                    filtered.append(item)
                    continue
            candidates = filtered
        candidates.sort(key=self._created_at_key, reverse=True)
        return {"ok": True, "items": candidates[:limit]}

    def _created_at_key(self, item: Dict[str, Any]) -> float:
        raw = item.get("created_at") or ""
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0
