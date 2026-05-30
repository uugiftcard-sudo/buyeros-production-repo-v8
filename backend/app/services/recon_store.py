"""Recon data persistence for BuyerOS (Supabase PostgREST).

We write receipt scan results into the recon tables created by migration 0010.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
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

    def fetch_refund_card_verification(self, *, verification_id: str) -> Optional[Dict[str, Any]]:
        if not self.supabase:
            return None
        res = (
            self.supabase.table("refund_card_verifications")
            .select(
                "verification_id,buyer_id,team_id,return_id,original_transaction_id,"
                "original_card_last4,refund_card_last4,refund_amount_hkd,card_match,"
                "card_verified,verification_status,risk_level,risk_flags,"
                "verified_by,verified_at,notes,created_at"
            )
            .eq("verification_id", verification_id)
            .limit(1)
            .execute()
        )
        rows = list(res.data or [])
        return rows[0] if rows else None

    def insert_refund_card_verification(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}
        res = self.supabase.table("refund_card_verifications").insert(payload).execute()
        return {"ok": True, "data": res.data}

    # ── Recon daily ────────────────────────────────────────────────────────────

    def fetch_recon_daily_records(self, *, date: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        res = (
            self.supabase.table("recon_daily")
            .select(
                "recon_id,team_id,date,period_type,"
                "total_declared_hkd,total_scanned_hkd,total_income_diff_hkd,"
                "total_returns_hkd,return_count,"
                "total_expenses_hkd,expense_count,"
                "total_missing_items,total_price_mismatches,total_risk_alerts,critical_alerts,"
                "total_commission_hkd,"
                "status,approved_by,approved_at,created_at"
            )
            .eq("date", date)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])

    def upsert_recon_daily(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}
        recon_id = payload.get("recon_id")
        if not recon_id:
            return {"ok": False, "error": "recon_id required"}
        try:
            self.supabase.table("recon_daily").upsert(payload, on_conflict="recon_id").execute()
            return {"ok": True, "recon_id": recon_id}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def run_daily_reconciliation(self, *, date: str) -> Dict[str, Any]:
        """Run daily reconciliation for all active teams on a given date.

        Returns a summary dict with teams_processed, total_declarations,
        total_bank_credits, matched_count, etc.
        """
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}

        teams = self.fetch_active_teams()
        teams_processed = 0
        total_declarations = 0
        total_bank_credits = 0
        matched_count = 0
        unmatched_declarations: List[str] = []
        unmatched_bank_credits: List[Dict[str, Any]] = []
        errors: List[str] = []

        for team in teams:
            team_id = team.get("team_id")
            if not team_id:
                continue
            try:
                decls = self.fetch_declarations_by_date(date=date, team_id=team_id)
                deposits = self.fetch_bank_deposits(date=date, team_id=team_id)

                total_declarations += len(decls)
                total_bank_credits += len(deposits)

                # Simple 1:1 matching: each declaration matches one deposit
                # In production this would be amount-based matching
                matched_count += min(len(decls), len(deposits))
                if len(decls) > len(deposits):
                    for d in decls[len(deposits):]:
                        unmatched_declarations.append(str(d.get("declaration_id") or ""))
                if len(deposits) > len(decls):
                    for dep in deposits[len(decls):]:
                        unmatched_bank_credits.append({
                            "ref": dep.get("transaction_ref"),
                            "amount": dep.get("amount_hkd"),
                            "desc": str(dep.get("description") or "")[:100],
                        })

                # Mark matched bank transactions as reconciled
                matched_tx_refs = [
                    str(dep.get("transaction_ref") or "")
                    for dep in deposits[:len(decls)]
                    if dep.get("transaction_ref")
                ]
                if matched_tx_refs:
                    self.mark_bank_transactions_reconciled(
                        transaction_refs=matched_tx_refs,
                        reconciled_with=f"recon-daily-{date}",
                        reconciled_by="system",
                    )

                recon_id = f"rd-{uuid.uuid4().hex[:12]}"
                payload: Dict[str, Any] = {
                    "recon_id": recon_id,
                    "team_id": team_id,
                    "date": date,
                    "period_type": "daily",
                    "total_declared_hkd": 0,
                    "total_scanned_hkd": 0,
                    "total_income_diff_hkd": 0,
                    "total_returns_hkd": 0,
                    "return_count": 0,
                    "total_expenses_hkd": 0,
                    "expense_count": 0,
                    "total_missing_items": 0,
                    "total_price_mismatches": 0,
                    "total_risk_alerts": 0,
                    "critical_alerts": 0,
                    "total_commission_hkd": 0,
                    "status": "draft",
                }
                self.upsert_recon_daily(payload=payload)
                teams_processed += 1
            except Exception as exc:
                errors.append(f"team {team_id}: {exc}")

        return {
            "ok": True,
            "date": date,
            "teams_processed": teams_processed,
            "total_declarations": total_declarations,
            "total_bank_credits": total_bank_credits,
            "matched_count": matched_count,
            "unmatched_declarations": unmatched_declarations,
            "unmatched_bank_credits": unmatched_bank_credits,
            "errors": errors,
        }

    def fetch_recon_daily_by_id(self, *, recon_id: str) -> Optional[Dict[str, Any]]:
        if not self.supabase:
            return None
        res = (
            self.supabase.table("recon_daily")
            .select(
                "recon_id,team_id,date,period_type,"
                "total_declared_hkd,total_scanned_hkd,total_income_diff_hkd,"
                "total_returns_hkd,return_count,"
                "total_expenses_hkd,expense_count,"
                "total_missing_items,total_price_mismatches,total_risk_alerts,critical_alerts,"
                "total_commission_hkd,"
                "status,approved_by,approved_at,created_at"
            )
            .eq("recon_id", recon_id)
            .limit(1)
            .execute()
        )
        rows = list(res.data or [])
        return rows[0] if rows else None

    # ── Bank transactions (read-only for reconciliation) ───────────────────────

    def fetch_bank_transactions(self, *, date: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        query = (
            self.supabase.table("bank_transactions")
            .select("transaction_ref,team_id,date,description,transaction_type,amount_hkd,balance_after_hkd,category,is_reconciled")
            .eq("date", date)
        )
        if team_id:
            query = query.eq("team_id", team_id)
        res = query.limit(5000).execute()
        return list(res.data or [])

    def fetch_bank_deposits(self, *, date: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        query = (
            self.supabase.table("bank_transactions")
            .select("transaction_ref,team_id,date,description,amount_hkd,balance_after_hkd")
            .eq("date", date)
            .gt("amount_hkd", 0)
        )
        if team_id:
            query = query.eq("team_id", team_id)
        res = query.limit(5000).execute()
        return list(res.data or [])

    # ── Purchase declarations (read-only for reconciliation) ───────────────────

    def fetch_declarations_by_date(
        self, *, date: str, team_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        query = (
            self.supabase.table("purchase_declarations")
            .select("declaration_id,buyer_id,team_id,date,status,declared_by,created_at")
            .eq("date", date)
        )
        if team_id:
            query = query.eq("team_id", team_id)
        res = query.limit(5000).execute()
        return list(res.data or [])

    # ── Recon teams ─────────────────────────────────────────────────────────────

    def fetch_active_teams(self) -> List[Dict[str, Any]]:
        if not self.supabase:
            return []
        res = (
            self.supabase.table("recon_teams")
            .select("team_id,team_name,leader_telegram_id,is_active,created_at")
            .eq("is_active", True)
            .execute()
        )
        return list(res.data or [])

    # ── Unmatched transactions marking ────────────────────────────────────────

    def mark_bank_transactions_reconciled(
        self, *, transaction_refs: List[str], reconciled_with: str, reconciled_by: str = "system"
    ) -> Dict[str, Any]:
        if not self.supabase or not transaction_refs:
            return {"ok": True, "updated": 0}
        try:
            self.supabase.table("bank_transactions").update(
                {
                    "is_reconciled": True,
                    "reconciled_with": reconciled_with,
                    "reconciled_by": reconciled_by,
                    "reconciled_at": datetime.now(timezone.utc).isoformat(),
                }
            ).in_("transaction_ref", transaction_refs).execute()
            return {"ok": True, "updated": len(transaction_refs)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
