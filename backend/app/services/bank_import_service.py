"""Bank statement import service (CSV -> parsed transactions -> Supabase).

This service is designed to support multiple banks by bank_code.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


from .bank_parsers.base import ParserRegistry
from .bank_parsers.generic import GenericCsvParser
from .bank_parsers.hsbc_hk import HsbcHkCsvParser


create_supabase_client = None
try:
    from supabase import create_client as _create_supabase_client  # type: ignore

    create_supabase_client = _create_supabase_client
except ImportError:
    create_supabase_client = None


class BankImportService:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        if url and key and create_supabase_client:
            self.supabase = create_supabase_client(url, key)

        self.parsers = ParserRegistry()
        self.parsers.register(GenericCsvParser())
        self.parsers.register(HsbcHkCsvParser())

    def configured(self) -> bool:
        return bool(self.supabase)

    def import_csv(
        self,
        *,
        bank_code: str,
        account_id: str,
        currency: str,
        content: str,
        team_id: Optional[str] = None,
        buyer_id: Optional[str] = None,
        statement_id: Optional[str] = None,
        source: str = "api",
        reference: str = "bank-import-csv",
    ) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}

        bank_code_norm = bank_code.lower().strip()
        parser = self.parsers.get(bank_code_norm) or self.parsers.get("generic")
        if not parser:
            return {"ok": False, "error": "no_parser"}

        parsed = parser.parse(content=content, account_id=account_id, currency=currency)
        if not parsed.ok:
            return {
                "ok": False,
                "error": "parse_failed",
                "errors": parsed.errors,
                "bank_code": bank_code_norm,
                "account_id": account_id,
            }

        return self._persist(
            bank_code=bank_code_norm,
            account_id=account_id,
            currency=parsed.currency,
            team_id=team_id,
            buyer_id=buyer_id,
            statement_id=statement_id,
            source=source,
            reference=reference,
            raw_text=content,
            transactions=[
                {
                    "date": t.date,
                    "description": t.description,
                    "amount": t.amount,
                    "currency": t.currency,
                    "balance": t.balance,
                    "reference": t.reference,
                }
                for t in parsed.transactions
            ],
        )

    def import_manual(
        self,
        *,
        bank_code: str,
        account_id: str,
        currency: str,
        transactions: List[Dict[str, Any]],
        team_id: Optional[str] = None,
        buyer_id: Optional[str] = None,
        statement_id: Optional[str] = None,
        source: str = "api",
        reference: str = "bank-import-manual",
        raw_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.supabase:
            return {"ok": False, "error": "supabase_not_configured"}

        bank_code_norm = bank_code.lower().strip()
        cur = (currency or "").upper().strip()
        if cur not in ("HKD", "GBP", "USDT"):
            return {"ok": False, "error": "unsupported_currency"}

        return self._persist(
            bank_code=bank_code_norm,
            account_id=account_id,
            currency=cur,
            team_id=team_id,
            buyer_id=buyer_id,
            statement_id=statement_id,
            source=source,
            reference=reference,
            raw_text=raw_text,
            transactions=transactions,
        )

    def _persist(
        self,
        *,
        bank_code: str,
        account_id: str,
        currency: str,
        team_id: Optional[str],
        buyer_id: Optional[str],
        statement_id: Optional[str],
        source: str,
        reference: str,
        transactions: List[Dict[str, Any]],
        raw_text: Optional[str],
    ) -> Dict[str, Any]:
        statement_id = statement_id or f"stmt-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Hash raw_text if provided; else hash transactions
        if raw_text is not None:
            digest = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()[:24]
        else:
            digest = hashlib.sha256(str(transactions).encode("utf-8", errors="ignore")).hexdigest()[:24]

        # Idempotency: bank_code + account_id + file_hash
        try:
            existing = (
                self.supabase.table("bank_statements")
                .select("statement_id")
                .eq("bank_code", bank_code)
                .eq("account_id", account_id)
                .eq("file_hash", digest)
                .limit(1)
                .execute()
            ).data
            if existing:
                return {
                    "ok": True,
                    "statement_id": existing[0].get("statement_id"),
                    "bank_code": bank_code,
                    "account_id": account_id,
                    "currency": currency,
                    "transactions": None,
                    "period_start": None,
                    "period_end": None,
                    "file_hash": digest,
                    "idempotent": True,
                }
        except Exception:
            # If schema/table doesn't support query yet, proceed with insert
            pass

        # Idempotency check return shape
        dates = [str(t.get("date") or "") for t in transactions if t.get("date")]
        if not dates:
            return {"ok": False, "error": "missing_dates"}
        period_start = min(dates)
        period_end = max(dates)

        statement_payload: Dict[str, Any] = {
            "statement_id": statement_id,
            "team_id": team_id,
            "buyer_id": buyer_id,
            "bank_code": bank_code,
            "account_id": account_id,
            "currency": currency,
            "period_start": period_start,
            "period_end": period_end,
            "imported_at": now,
            "import_source": source,
            "reference": reference,
            "file_hash": digest,
            "status": "imported",
            "raw_text": raw_text,
        }

        self.supabase.table("bank_statements").insert(statement_payload).execute()

        tx_rows: List[Dict[str, Any]] = []
        for t in transactions:
            tx_id = f"tx-{uuid.uuid4().hex[:12]}"
            tx_rows.append(
                {
                    "transaction_id": tx_id,
                    "statement_id": statement_id,
                    "team_id": team_id,
                    "buyer_id": buyer_id,
                    "date": t.get("date"),
                    "description": (t.get("description") or "")[:500],
                    "amount": t.get("amount"),
                    "currency": t.get("currency") or currency,
                    "balance": t.get("balance"),
                    "reference": t.get("reference"),
                    "is_reconciled": False,
                    "created_at": now,
                }
            )

        chunk_size = 500
        for i in range(0, len(tx_rows), chunk_size):
            self.supabase.table("bank_transactions").insert(tx_rows[i : i + chunk_size]).execute()

        return {
            "ok": True,
            "statement_id": statement_id,
            "bank_code": bank_code,
            "account_id": account_id,
            "currency": currency,
            "transactions": len(tx_rows),
            "period_start": period_start,
            "period_end": period_end,
            "file_hash": digest,
        }
