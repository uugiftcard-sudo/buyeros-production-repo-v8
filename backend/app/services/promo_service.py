"""Promo campaign tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from ..memory_store import MemoryStore


class PromoService:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store

    def create_campaign(
        self,
        *,
        name: str,
        offer: str,
        channel: str = "web",
        budget_hkd: float = 0,
        utm_source: Optional[str] = None,
        utm_campaign: Optional[str] = None,
    ) -> dict[str, Any]:
        campaign_id = f"camp-{uuid4().hex[:8]}"
        campaign = {
            "campaign_id": campaign_id,
            "name": name,
            "offer": offer,
            "channel": channel,
            "budget_hkd": budget_hkd,
            "utm_source": utm_source,
            "utm_campaign": utm_campaign,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "promo", "campaigns"], campaign_id, campaign, created_by="promo")
        return {"ok": True, "campaign": campaign}

    def list_campaigns(self, *, limit: int = 20) -> dict[str, Any]:
        return {"ok": True, "items": self.memory.search_memory(namespace_prefix=("buyeros", "promo", "campaigns"), limit=limit)}

    def record_event(
        self,
        *,
        campaign_id: str,
        event_type: str,
        value_hkd: float = 0,
        source: str = "api",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        event_id = f"evt-{uuid4().hex[:8]}"
        event = {
            "event_id": event_id,
            "campaign_id": campaign_id,
            "event_type": event_type,
            "value_hkd": value_hkd,
            "source": source,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_memory(["buyeros", "promo", "events"], event_id, event, created_by="promo")
        return {"ok": True, "event": event}

    def metrics(self, *, campaign_id: Optional[str] = None) -> dict[str, Any]:
        events = self.memory.search_memory(namespace_prefix=("buyeros", "promo", "events"), limit=500)
        counts: dict[str, int] = {}
        revenue = 0.0
        for item in events:
            event = item.get("content") or {}
            if campaign_id and event.get("campaign_id") != campaign_id:
                continue
            event_type = str(event.get("event_type") or "unknown")
            counts[event_type] = counts.get(event_type, 0) + 1
            revenue += float(event.get("value_hkd") or 0)
        return {"ok": True, "counts": counts, "revenue_hkd": revenue}
