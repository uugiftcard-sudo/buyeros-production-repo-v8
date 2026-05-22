"""AI team task board for BuyerOS."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from ..memory_store import MemoryStore
from .canonical_workspace import CANONICAL_WORKSPACES, normalize_workspace


class TaskBoardService:
    """Persist cross-provider tasks and lifecycle state."""

    LANES = {
        "buyeros": "BuyerOS Core",
        "cloth": "CLOTH 網店自動系統",
        "xau": "XAU 中控",
    }
    LANE_ALIASES = {
        "buyeros": "buyeros",
        "ai_team": "buyeros",
        "ai-solo-team": "buyeros",
        "ai_solo_team": "buyeros",
        "report": "cloth",
        "commerce": "cloth",
        "promo": "xau",
        "xau_promo": "xau",
        "xau-team": "xau",
        "shop": "cloth",
    }

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    @classmethod
    def normalize_lane(cls, lane: str | None) -> str:
        raw = (lane or "").strip()
        normalized = cls.LANE_ALIASES.get(raw, raw)
        canonical = set(CANONICAL_WORKSPACES)
        return normalize_workspace(normalized if normalized in canonical else raw)

    @classmethod
    def normalize_task_content(cls, content: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(content)
        lane = cls.normalize_lane(str(normalized.get("lane") or (normalized.get("payload") or {}).get("project") or ""))
        normalized["lane"] = lane
        normalized["lane_label"] = cls.LANES[lane]
        payload = normalized.get("payload")
        if isinstance(payload, dict):
            normalized["payload"] = {**payload, "project": cls.normalize_lane(str(payload.get("project") or lane))}
        return normalized

    def create_task(
        self,
        *,
        title: str,
        lane: str = "buyeros",
        owner_provider: str = "openai",
        priority: str = "P1",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        task_id = f"task-{uuid4().hex[:8]}"
        normalized_lane = self.normalize_lane(lane)
        normalized_payload = dict(payload or {})
        if "project" in normalized_payload:
            normalized_payload["project"] = self.normalize_lane(str(normalized_payload.get("project") or normalized_lane))
        content = {
            "task_id": task_id,
            "title": title,
            "lane": normalized_lane,
            "lane_label": self.LANES[normalized_lane],
            "owner_provider": owner_provider,
            "priority": priority,
            "status": "queued",
            "payload": normalized_payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "tasks"], task_id, content, created_by="task_board_service")
        return {"ok": True, "task": content}

    def list_tasks(self, *, lane: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        tasks = self.memory.search_memory(namespace_prefix=("buyeros", "tasks"), limit=limit)
        for item in tasks:
            content = item.get("content")
            if isinstance(content, dict):
                item["content"] = self.normalize_task_content(content)
        if lane:
            normalized_lane = self.normalize_lane(lane)
            tasks = [item for item in tasks if (item.get("content") or {}).get("lane") == normalized_lane]
        return {"ok": True, "lanes": self.LANES, "items": tasks}

    def update_status(self, *, task_id: str, status: str, note: Optional[str] = None) -> Dict[str, Any]:
        existing = self.memory.search_memory(namespace_prefix=("buyeros", "tasks"), memory_key=task_id, limit=1)
        content = dict((existing[0].get("content") if existing else {}) or {})
        if not content:
            content = {
                "task_id": task_id,
                "title": task_id,
                "lane": "buyeros",
                "lane_label": self.LANES["buyeros"],
                "owner_provider": "openai",
                "priority": "P1",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        content = self.normalize_task_content(content)
        content.update({"status": status, "note": note, "updated_at": datetime.now(timezone.utc).isoformat()})
        self.memory.save_memory(["buyeros", "tasks"], task_id, content, created_by="task_board_service")
        return {"ok": True, "task": content}

    def run_task(self, *, task_id: str, result: str, provider: str = "openai") -> Dict[str, Any]:
        run_id = f"run-{uuid4().hex[:10]}"
        run = {
            "run_id": run_id,
            "task_id": task_id,
            "provider": provider,
            "result": result,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "task_runs"], run_id, run, created_by="task_board_service")
        self.update_status(task_id=task_id, status="completed", note=f"Completed by {provider}")
        return {"ok": True, "run": run}
