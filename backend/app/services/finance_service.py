"""Finance service with chained data source priority.

Priority: Google Sheets → Finance API → Local memory estimate
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict

import requests

from ..memory_store import MemoryStore
from .finance_sheets import FinanceSheetsService

logger = logging.getLogger(__name__)


class FinanceService:
    def __init__(self, memory_store: MemoryStore) -> None:
        self.memory = memory_store
        self.sheets = FinanceSheetsService()
        self.base_url = os.getenv("FINANCE_API_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("FINANCE_API_KEY", "")

    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def get_profit_summary(self) -> Dict[str, Any]:
        # 1. Try Google Sheets
        if self.sheets.configured():
            result = self.sheets.get_profit_summary()
            if result.get("data", {}).get("note", "").startswith("數據來源：Google"):
                return result
            logger.warning(
                "Google Sheets returned error, falling back: %s",
                result.get("data", {}).get("note"),
            )

        # 2. Try remote Finance API
        if self.configured():
            try:
                response = requests.get(
                    f"{self.base_url}/profit/summary",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=20,
                )
                response.raise_for_status()
                return {"ok": True, "source": "remote_finance_api", "data": response.json()}
            except Exception as exc:
                logger.error("Finance API profit call failed: %s", exc)

        # 3. Fallback: infer from locally stored refund records
        refunds = self.memory.search_memory(
            namespace_prefix=("buyeros", "refunds"), limit=50
        )
        refund_count = len(refunds)
        gross_profit = max(0, 50000 - refund_count * 500)
        return {
            "ok": True,
            "source": "local_estimate",
            "data": {
                "profit_hkd": gross_profit,
                "refund_count": refund_count,
                "note": "本地估算值，未接入正式財務 API。",
            },
        }

    def get_payout_schedule(self) -> Dict[str, Any]:
        # 1. Try Google Sheets
        if self.sheets.configured():
            result = self.sheets.get_payout_schedule()
            if result.get("data", {}).get("note", "").startswith("數據來源：Google"):
                return result

        # 2. Try remote Finance API
        if self.configured():
            try:
                response = requests.get(
                    f"{self.base_url}/payout/schedule",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=20,
                )
                response.raise_for_status()
                return {"ok": True, "source": "remote_finance_api", "data": response.json()}
            except Exception as exc:
                logger.error("Finance API payout call failed: %s", exc)

        # 3. Fallback: default schedule
        return {
            "ok": True,
            "source": "local_default",
            "data": {
                "next_payout_day": 5,
                "currency": "HKD",
                "note": "本地預設值，未接入正式財務 API。",
            },
        }
