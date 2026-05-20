"""Google Sheets finance service for BuyerOS.

Reads profit summaries and payout schedules from a shared Google Sheets
spreadsheet using the Sheets API v4.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class FinanceSheetsService:
    """Read-only finance data from Google Sheets.

    Supports two authentication methods (checked in priority order):
    1. Service account JSON (GOOGLE_SERVICE_ACCOUNT_JSON) — recommended for server-side
    2. API key (GOOGLE_SHEETS_API_KEY) — works for publicly shared sheets

    Spreadsheet layout expected:
      Sheet 1 name: "利潤" (Profit)
        Headers: A=月份, B=HKD金額, C=退款筆數
        Row 1: header, Row 2+: data

      Sheet 2 name: "出糧" (Payout)
        Headers: A=下次出糧日, B=幣種, C=狀態
        Row 1: header, Row 2+: data
    """

    SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(self) -> None:
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
        self._service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        self._api_key = os.getenv("GOOGLE_SHEETS_API_KEY", "")

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    # ── Auth ────────────────────────────────────────────────────────────────

    def configured(self) -> bool:
        return bool(self.spreadsheet_id and (self._service_account_json or self._api_key))

    def _auth_headers(self) -> Dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        # Service account: obtain access token via JWT assertion
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    def _get_access_token(self) -> str:
        if self._access_token and datetime.now().timestamp() < self._token_expiry:
            return self._access_token

        try:
            creds = json.loads(self._service_account_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid GOOGLE_SERVICE_ACCOUNT_JSON") from exc

        import time
        import jwt

        now = int(time.time())
        payload = {
            "iss": creds["client_email"],
            "sub": creds["client_email"],
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        assertion = jwt.encode(
            payload,
            creds["private_key"],
            algorithm="RS256",
        )

        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = datetime.now().timestamp() + data.get("expires_in", 3600) - 60
        return self._access_token

    def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.SHEETS_API}/{self.spreadsheet_id}/values:batchGet"
        resp = requests.get(url, params=params, headers=self._auth_headers(), timeout=20)
        resp.raise_for_status()
        return resp.json()

    # ── Public API ─────────────────────────────────────────────────────────

    def get_profit_summary(self) -> Dict[str, Any]:
        """Return the current month's profit row as a dict."""
        try:
            result = self._get({
                "ranges": "'利潤'!A1:C2",
                "valueRenderOption": "UNFORMATTED_VALUE",
            })
            rows = (result.get("valueRanges") or [{}])[0].get("values") or []
            if len(rows) < 2:
                return self._profit_fallback()

            month, profit_hkd, refund_count = rows[1]
            return {
                "ok": True,
                "source": "google_sheets",
                "data": {
                    "month": str(month),
                    "profit_hkd": float(profit_hkd),
                    "refund_count": int(refund_count),
                    "note": "數據來源：Google Sheets。",
                },
            }
        except Exception as exc:
            logger.error("Failed to read profit from Google Sheets: %s", exc)
            return self._profit_fallback()

    def get_payout_schedule(self) -> Dict[str, Any]:
        """Return the next payout row."""
        try:
            result = self._get({
                "ranges": "'出糧'!A1:C2",
                "valueRenderOption": "UNFORMATTED_VALUE",
            })
            rows = (result.get("valueRanges") or [{}])[0].get("values") or []
            if len(rows) < 2:
                return self._payout_fallback()

            next_day, currency, status = rows[1]
            return {
                "ok": True,
                "source": "google_sheets",
                "data": {
                    "next_payout_day": int(next_day) if isinstance(next_day, (int, float)) else 5,
                    "currency": str(currency) if currency else "HKD",
                    "status": str(status) if status else "unknown",
                    "note": "數據來源：Google Sheets。",
                },
            }
        except Exception as exc:
            logger.error("Failed to read payout from Google Sheets: %s", exc)
            return self._payout_fallback()

    # ── Fallbacks ─────────────────────────────────────────────────────────

    def _profit_fallback(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "source": "google_sheets_error",
            "data": {
                "month": "",
                "profit_hkd": 0,
                "refund_count": 0,
                "note": "無法從 Google Sheets 讀取盈利數據，請檢查 Sheets 設定。",
            },
        }

    def _payout_fallback(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "source": "google_sheets_error",
            "data": {
                "next_payout_day": 5,
                "currency": "HKD",
                "status": "unknown",
                "note": "無法從 Google Sheets 讀取出糧日程，請檢查 Sheets 設定。",
            },
        }
