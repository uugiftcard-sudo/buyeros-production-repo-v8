"""Project registry for BuyerOS / AIOS.

BuyerOS canonical projects are:
- buyer_ai: AI OS core plus buyer reports and sourcing intelligence
- commerce: e-commerce operations
- xau: campaign/promotion workspace
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..memory_store import MemoryStore
from .canonical_workspace import CANONICAL_WORKSPACES, normalize_workspace


class ProjectRegistryService:
    PROJECT_ALIASES = {
        "buyer_ai": "buyer_ai",
        "buyeros": "buyer_ai",
        "ai_team": "buyer_ai",
        "ai-team": "buyer_ai",
        "ai_solo_team": "buyer_ai",
        "ai-solo-team": "buyer_ai",
        "buyer_report": "buyer_ai",
        "buyer-report": "buyer_ai",
        "report": "buyer_ai",
        "reporting": "buyer_ai",
        "commerce": "commerce",
        "cloth": "commerce",
        "orders": "commerce",
        "order": "commerce",
        "shop": "commerce",
        "xau": "xau",
        "promo": "xau",
        "xau_promo": "xau",
        "xau-team": "xau",
        "xau_team": "xau",
        "xaupromo": "xau",
        "xau-promo": "xau",
    }
    DEFAULT_PROJECTS: List[Dict[str, Any]] = [
        {
            "project_id": "buyer_ai",
            "name": "買手 AI 中樞",
            "kind": "buyer_ai",
            "source": {"repo": "buyeros-production-repo-v8"},
            "notes": "BuyerOS / AI Team / Context Hub / Telegram / 買手 Report / 採購 ROI",
        },
        {
            "project_id": "commerce",
            "name": "網店自動系統",
            "kind": "commerce_ops",
            "source": {"path": "/Users/rubykan/Documents/CLOTH"},
            "notes": "AI 虛擬主播帶貨 / 訂單 / 庫存 / 客服 / 網店收支報表 / Shopify / TikTok / 資料同步",
        },
        {
            "project_id": "xau",
            "name": "XAU 中控",
            "kind": "promo",
            "source": {"path": "/Users/rubykan/Documents/XAU", "github": "uugiftcard-sudo/XAU"},
            "notes": "AI 直播 / 虛擬主播 / promo / campaign / conversion / metrics / funnel",
        },
    ]

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    @classmethod
    def normalize_project_id(cls, project_id: str | None) -> str:
        raw = (project_id or "").strip()
        if not raw:
            return "buyer_ai"
        canonical = set(CANONICAL_WORKSPACES)
        return normalize_workspace(cls.PROJECT_ALIASES.get(raw, raw if raw in canonical else raw))

    def list_projects(self, *, limit: int = 50) -> Dict[str, Any]:
        defaults_by_id = {item["project_id"]: item for item in self.DEFAULT_PROJECTS}
        items = self.memory.search_memory(namespace_prefix=("buyeros", "projects"), limit=max(limit, 100))
        found_ids = {
            self.normalize_project_id(str((item.get("content") or {}).get("project_id") or item.get("memory_key") or ""))
            for item in items
        }
        for item in self.DEFAULT_PROJECTS:
            if item["project_id"] not in found_ids:
                self.upsert_project(project_id=item["project_id"], content=item, created_by="project_registry")

        items = self.memory.search_memory(namespace_prefix=("buyeros", "projects"), limit=max(limit, 100))
        latest_by_project: Dict[str, Dict[str, Any]] = {}
        for item in items:
            raw_id = str((item.get("content") or {}).get("project_id") or item.get("memory_key") or "")
            project_id = self.normalize_project_id(raw_id)
            if project_id not in defaults_by_id:
                continue
            current = latest_by_project.get(project_id)
            if current is None or str(item.get("created_at") or "") >= str(current.get("created_at") or ""):
                latest_by_project[project_id] = item

        output: List[Dict[str, Any]] = []
        for default in self.DEFAULT_PROJECTS:
            project_id = default["project_id"]
            item = dict(latest_by_project.get(project_id) or {})
            content = dict(default)
            existing_content = item.get("content") if isinstance(item.get("content"), dict) else {}
            source = existing_content.get("source") if isinstance(existing_content, dict) else None
            if source:
                content["source"] = source
            content["project_id"] = project_id
            content["normalized_project_id"] = project_id
            item.update({"memory_key": project_id, "content": content})
            output.append(item)

        return {"ok": True, "items": output[:limit]}

    def upsert_project(self, *, project_id: str, content: Dict[str, Any], created_by: str = "api") -> Dict[str, Any]:
        project_id = self.normalize_project_id(project_id)
        payload = dict(content)
        payload["project_id"] = project_id
        payload["normalized_project_id"] = project_id
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.memory.save_memory(["buyeros", "projects"], project_id, payload, created_by=created_by)
        return {"ok": True, "project": payload}

    def get_project(self, *, project_id: str) -> Optional[Dict[str, Any]]:
        project_id = self.normalize_project_id(project_id)
        items = self.memory.search_memory(namespace_prefix=("buyeros", "projects"), memory_key=project_id, limit=1)
        if not items:
            for item in self.DEFAULT_PROJECTS:
                if item["project_id"] == project_id:
                    return dict(item)
            return None
        content = dict(items[0].get("content") or {})
        content["project_id"] = project_id
        content["normalized_project_id"] = project_id
        return content
