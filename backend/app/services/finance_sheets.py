"""Google Sheets-backed finance data source."""

from __future__ import annotations

import json
import os
from typing import Any

import requests


class FinanceSheetsService:
    def __init__(self) -> None:
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()
        self.api_key = os.getenv("GOOGLE_SHEETS_API_KEY", "").strip()
        self.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

    def configured(self) -> bool:
        if not self.spreadsheet_id:
            return False
        return bool(self.api_key or self._service_account_configured())

    def get_profit_summary(self) -> dict[str, Any]:
        try:
            values = self._fetch_values("Profit!A:C")
            row = self._first_data_row(values)
            return {
                "ok": True,
                "source": "google_sheets",
                "data": {
                    "month": str(row[0]),
                    "profit_hkd": float(row[1]),
                    "refund_count": int(row[2]),
                    "note": "數據來源：Google Sheets。",
                },
            }
        except Exception as exc:
            return {
                "ok": True,
                "source": "google_sheets_error",
                "data": {
                    "profit_hkd": 0,
                    "refund_count": 0,
                    "note": f"Google Sheets unavailable: {exc}",
                },
            }

    def get_payout_schedule(self) -> dict[str, Any]:
        try:
            values = self._fetch_values("Payout!A:C")
            row = self._first_data_row(values)
            return {
                "ok": True,
                "source": "google_sheets",
                "data": {
                    "next_payout_day": int(row[0]),
                    "currency": str(row[1]),
                    "status": str(row[2]),
                    "note": "數據來源：Google Sheets。",
                },
            }
        except Exception as exc:
            return {
                "ok": True,
                "source": "google_sheets_error",
                "data": {
                    "next_payout_day": 5,
                    "currency": "HKD",
                    "status": "pending",
                    "note": f"Google Sheets unavailable: {exc}",
                },
            }

    def _fetch_values(self, range_name: str) -> list[list[Any]]:
        if not self.api_key:
            raise RuntimeError("service account Google Sheets access is not implemented in local smoke")
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values:batchGet"
        response = requests.get(url, params={"ranges": range_name, "key": self.api_key}, timeout=20)
        response.raise_for_status()
        body = response.json()
        ranges = body.get("valueRanges") or []
        if not ranges:
            return []
        return ranges[0].get("values") or []

    @staticmethod
    def _first_data_row(values: list[list[Any]]) -> list[Any]:
        if len(values) < 2:
            raise ValueError("no data rows")
        return values[1]

    def _service_account_configured(self) -> bool:
        if not self.service_account_json:
            return False
        try:
            payload = json.loads(self.service_account_json)
        except json.JSONDecodeError:
            return False
        return bool(payload.get("client_email") and payload.get("private_key"))
