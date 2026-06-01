"""Memory-backed task board for BuyerOS operator workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from ..memory_store import MemoryStore
from .canonical_workspace import normalize_workspace


CANONICAL_PROJECTS = {
    "buyer_ai": {"project_id": "buyer_ai", "name": "買手 AI 中樞"},
    "commerce": {"project_id": "commerce", "name": "網店自動系統"},
    "xau": {"project_id": "xau", "name": "XAU 中控"},
}


class TaskBoardService:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def normalize_lane(self, lane: str) -> str:
        return normalize_workspace(lane)

    def create_task(
        self,
        *,
        title: str,
        lane: str,
        owner_provider: str,
        priority: str = "P2",
        payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        normalized_lane = self.normalize_lane(lane)
        task_id = f"task-{uuid4().hex[:8]}"
        task = {
            "task_id": task_id,
            "title": title,
            "lane": normalized_lane,
            "lane_label": CANONICAL_PROJECTS[normalized_lane]["name"],
            "owner_provider": owner_provider,
            "priority": priority,
            "status": "queued",
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "tasks"], task_id, task, created_by="task_board")
        return {"ok": True, "task": task}

    def update_status(self, *, task_id: str, status: str, note: Optional[str] = None) -> dict[str, Any]:
        task = self._get_task(task_id) or {"task_id": task_id, "lane": "buyer_ai", "lane_label": CANONICAL_PROJECTS["buyer_ai"]["name"]}
        task = {**task, "status": status, "note": note, "updated_at": datetime.now(timezone.utc).isoformat()}
        self.memory.save_memory(["buyeros", "tasks"], task_id, task, created_by="task_board")
        return {"ok": True, "task": task}

    def run_task(self, *, task_id: str, result: str, provider: str) -> dict[str, Any]:
        run_id = f"run-{uuid4().hex[:8]}"
        run = {
            "run_id": run_id,
            "task_id": task_id,
            "result": result,
            "provider": provider,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "task_runs"], run_id, run, created_by=provider)
        self.update_status(task_id=task_id, status="completed", note=f"completed by {provider}")
        return {"ok": True, "run": run}

    def list_tasks(self, *, lane: Optional[str] = None, limit: int = 50) -> dict[str, Any]:
        normalized = self.normalize_lane(lane) if lane else None
        items = self.memory.search_memory(namespace_prefix=("buyeros", "tasks"), limit=max(limit * 3, limit))
        if normalized:
            items = [item for item in items if (item.get("content") or {}).get("lane") == normalized]
        return {"ok": True, "items": items[-limit:]}

    def normalize_task_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        return dict(item.get("content") or {})

    def _get_task(self, task_id: str) -> dict[str, Any] | None:
        items = self.memory.search_memory(namespace_prefix=("buyeros", "tasks"), memory_key=task_id, limit=1)
        return dict(items[-1].get("content") or {}) if items else None
