"""Canonical BuyerOS project registry."""

from __future__ import annotations

from typing import Any

from ..memory_store import MemoryStore
from .canonical_workspace import normalize_workspace


CANONICAL_PROJECTS = {
    "buyer_ai": {"project_id": "buyer_ai", "name": "買手 AI 中樞"},
    "commerce": {"project_id": "commerce", "name": "網店自動系統"},
    "xau": {"project_id": "xau", "name": "XAU 中控"},
}


class ProjectRegistryService:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def list_projects(self, *, limit: int = 50) -> dict[str, Any]:
        return {"ok": True, "items": [{"namespace": ["buyeros", "projects"], "memory_key": key, "content": value} for key, value in list(CANONICAL_PROJECTS.items())[:limit]]}

    def get_project(self, *, project_id: str) -> dict[str, Any] | None:
        key = normalize_workspace(project_id)
        return CANONICAL_PROJECTS.get(key)

    def upsert_project(self, *, project_id: str, content: dict[str, Any], created_by: str = "api") -> dict[str, Any]:
        key = normalize_workspace(project_id)
        payload = {**CANONICAL_PROJECTS.get(key, {}), **content, "project_id": key}
        self.memory.save_memory(["buyeros", "projects"], key, payload, created_by=created_by)
        return {"ok": True, "project": payload}
