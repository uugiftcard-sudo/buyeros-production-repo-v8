"""XAU promo campaign tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from ..memory_store import MemoryStore


class PromoService:
    """Store XAU promo campaigns, assets, and conversion events."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def create_campaign(
        self,
        *,
        name: str,
        offer: str,
        channel: str = "manual",
        budget_hkd: float = 0,
        utm_source: str = "buyeros",
        utm_campaign: Optional[str] = None,
    ) -> Dict[str, Any]:
        campaign_id = f"xau-{uuid4().hex[:8]}"
        slug = (utm_campaign or name).lower().replace(" ", "-")
        payload = {
            "campaign_id": campaign_id,
            "project_id": "xau",
            "project": "xau",
            "name": name,
            "offer": offer,
            "channel": channel,
            "budget_hkd": budget_hkd,
            "utm": {
                "source": utm_source,
                "campaign": slug,
            },
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "promo", "campaigns"], campaign_id, payload, created_by="promo_service")
        return {"ok": True, "campaign": payload}

    def list_campaigns(self, *, limit: int = 20) -> Dict[str, Any]:
        return {
            "ok": True,
            "items": self.memory.search_memory(namespace_prefix=("buyeros", "promo", "campaigns"), limit=limit),
        }

    def record_event(
        self,
        *,
        campaign_id: str,
        event_type: str,
        value_hkd: float = 0,
        source: str = "ui",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event_id = f"evt-{uuid4().hex[:10]}"
        payload = {
            "event_id": event_id,
            "project_id": "xau",
            "project": "xau",
            "campaign_id": campaign_id,
            "event_type": event_type,
            "value_hkd": value_hkd,
            "source": source,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "promo", "events"], event_id, payload, created_by="promo_service")
        return {"ok": True, "event": payload}

    def metrics(self, *, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        events = self.memory.search_memory(namespace_prefix=("buyeros", "promo", "events"), limit=200)
        if campaign_id:
            events = [item for item in events if (item.get("content") or {}).get("campaign_id") == campaign_id]
        counts: Dict[str, int] = {}
        revenue = 0.0
        for item in events:
            content = item.get("content") or {}
            event_type = str(content.get("event_type") or "unknown")
            counts[event_type] = counts.get(event_type, 0) + 1
            if event_type in {"conversion", "purchase", "lead"}:
                revenue += float(content.get("value_hkd") or 0)
        return {"ok": True, "campaign_id": campaign_id, "counts": counts, "revenue_hkd": round(revenue, 2), "events": events[:20]}
