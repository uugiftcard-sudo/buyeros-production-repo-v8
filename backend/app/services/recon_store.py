"""Recon data persistence for BuyerOS (Supabase PostgREST).

We write receipt scan results into the recon tables created by migration 0010.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


create_supabase_client = None
try:
    from supabase import create_client as _create_supabase_client  # type: ignore

    create_supabase_client = _create_supabase_client
except ImportError:
    create_supabase_client = None


class ReconStore:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        if url and key and create_supabase_client:
            self.supabase = create_supabase_client(url, key)

    def configured(self) -> bool:
        return bool(self.supabase)

    def fetch_declaration_items(self, *, declaration_id: str) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        res = (
            self.supabase.table("declaration_items")
            .select("id,declaration_id,item_name,item_description,quantity,unit_price_hkd,subtotal_hkd")
            .eq("declaration_id", declaration_id)
            .execute()
        )
        return list(res.data or [])

    def fetch_receipt_items(self, *, scan_id: str) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        res = (
            self.supabase.table("receipt_items")
            .select("id,scan_id,item_name,quantity,unit_price_hkd,subtotal_hkd,ai_confidence")
            .eq("scan_id", scan_id)
            .execute()
        )
        return list(res.data or [])

    def insert_receipt_scan(
        self,
        *,
        scan_id: str,
        buyer_id: str,
        team_id: Optional[str],
        declaration_id: Optional[str],
        scan_date: str,
        image_url: str,
        raw_text: Optional[str],
        total_amount_hkd: Optional[int],
        ai_provider: str,
        ai_confidence: Optional[float],
        ai_model: Optional[str],
        raw: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}

        payload: Dict[str, Any] = {
            "scan_id": scan_id,
            "buyer_id": buyer_id,
            "team_id": team_id,
            "declaration_id": declaration_id,
            "date": scan_date,
            "image_url": image_url,
            "raw_text": raw_text,
            "total_amount_hkd": total_amount_hkd,
            "currency": "HKD",
            "scan_status": "completed",
            "ai_provider": ai_provider,
            "ai_confidence": ai_confidence,
        }

        if raw is not None:
            payload["scan_error"] = None

        res = self.supabase.table("receipt_scans").insert(payload).execute()
        return {"ok": True, "data": res.data}

    def insert_receipt_items(self, *, scan_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}
        rows = []
        for it in items:
            rows.append(
                {
                    "scan_id": scan_id,
                    "item_name": it.get("item_name"),
                    "quantity": it.get("quantity", 1),
                    "unit_price_hkd": it.get("unit_price_hkd"),
                    "subtotal_hkd": it.get("subtotal_hkd"),
                    "ai_confidence": it.get("ai_confidence"),
                }
            )
        if not rows:
            return {"ok": True, "data": []}
        res = self.supabase.table("receipt_items").insert(rows).execute()
        return {"ok": True, "data": res.data}

    def insert_item_comparison(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}
        res = self.supabase.table("item_comparisons").insert(payload).execute()
        return {"ok": True, "data": res.data}

    def fetch_return(self, *, return_id: str) -> Optional[Dict[str, Any]]:
        if not self.supabase:
            return None
        res = (
            self.supabase.table("returns")
            .select("return_id,buyer_id,team_id,declaration_id,date,refund_amount_hkd,image_url,scan_status,status")
            .eq("return_id", return_id)
            .limit(1)
            .execute()
        )
        rows = list(res.data or [])
        return rows[0] if rows else None

    def fetch_payment_cards_for_buyer(self, *, buyer_id: str) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        res = (
            self.supabase.table("payment_cards")
            .select("card_id,buyer_id,team_id,card_last4,is_verified,is_active")
            .eq("buyer_id", buyer_id)
            .execute()
        )
        return list(res.data or [])

    def insert_refund_card_verification(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}
        res = self.supabase.table("refund_card_verifications").insert(payload).execute()
        return {"ok": True, "data": res.data}
