"""Receipt scanning via OpenRouter Vision.

This service accepts an image URL and returns a structured representation of a receipt
(items, totals, vendor hints) using an OpenRouter model that supports vision.

All monetary amounts are returned as HKD cents (integer).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import date as date_type
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class ReceiptItem:
    item_name: str
    quantity: int
    unit_price_hkd: Optional[int]
    subtotal_hkd: Optional[int]
    ai_confidence: Optional[float]


@dataclass
class ReceiptVisionResult:
    ok: bool
    provider: str
    model: str
    scan_id: str
    date: Optional[str]
    merchant: Optional[str]
    currency: str
    total_amount_hkd: Optional[int]
    items: List[ReceiptItem]
    raw: Dict[str, Any]
    error: Optional[str] = None


class ReceiptVisionService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.endpoint = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.model = os.getenv("OPENROUTER_MODEL_VISION", "anthropic/claude-3.5-sonnet")

    def configured(self) -> bool:
        return bool(self.api_key)

    def extract_receipt(
        self,
        *,
        image_url: str,
        scan_id: Optional[str] = None,
        receipt_date: Optional[str] = None,
    ) -> ReceiptVisionResult:
        scan_id = scan_id or f"scan-{uuid.uuid4().hex[:12]}"

        if not image_url:
            return ReceiptVisionResult(
                ok=False,
                provider="openrouter",
                model=self.model,
                scan_id=scan_id,
                date=receipt_date,
                merchant=None,
                currency="HKD",
                total_amount_hkd=None,
                items=[],
                raw={},
                error="missing_image_url",
            )

        if not self.configured():
            return ReceiptVisionResult(
                ok=False,
                provider="openrouter",
                model=self.model,
                scan_id=scan_id,
                date=receipt_date,
                merchant=None,
                currency="HKD",
                total_amount_hkd=None,
                items=[],
                raw={},
                error="OPENROUTER_API_KEY_not_configured",
            )

        system = (
            "You are a receipt extraction engine. "
            "Return ONLY valid JSON with the schema described. "
            "All amounts must be integer HKD cents. Do not include commentary."
        )

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "date": {"type": ["string", "null"], "description": "YYYY-MM-DD if possible"},
                "merchant": {"type": ["string", "null"]},
                "currency": {"type": "string", "default": "HKD"},
                "total_amount_hkd": {"type": ["integer", "null"], "description": "Total in HKD cents"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "item_name": {"type": "string"},
                            "quantity": {"type": "integer", "default": 1},
                            "unit_price_hkd": {"type": ["integer", "null"]},
                            "subtotal_hkd": {"type": ["integer", "null"]},
                            "ai_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                        },
                        "required": ["item_name", "quantity", "unit_price_hkd", "subtotal_hkd", "ai_confidence"],
                    },
                },
            },
            "required": ["date", "merchant", "currency", "total_amount_hkd", "items"],
        }

        user_prompt = {
            "task": "Extract receipt structured data from this image.",
            "requirements": [
                "Return JSON only.",
                "If quantity is missing, default to 1.",
                "Convert HKD dollars to cents (e.g. 12.5 -> 1250).",
                "If a value is unknown, use null.",
            ],
            "schema": schema,
            "hints": {
                "receipt_date": receipt_date,
                "currency": "HKD",
            },
            "image_url": image_url,
        }

        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": json.dumps(user_prompt, ensure_ascii=False)},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ]

        started = time.perf_counter()
        try:
            resp = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (((data.get("choices") or [])[0] or {}).get("message") or {}).get("content")
            parsed = self._parse_json_only(text)
            normalized = self._normalize(parsed)
            normalized_raw = {
                "openrouter": {
                    "id": data.get("id"),
                    "model": data.get("model") or self.model,
                    "usage": data.get("usage"),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                },
                "parsed": parsed,
            }
            return ReceiptVisionResult(
                ok=True,
                provider="openrouter",
                model=data.get("model") or self.model,
                scan_id=scan_id,
                date=normalized["date"],
                merchant=normalized["merchant"],
                currency=normalized["currency"],
                total_amount_hkd=normalized["total_amount_hkd"],
                items=[ReceiptItem(**item) for item in normalized["items"]],
                raw=normalized_raw,
            )
        except Exception as exc:
            return ReceiptVisionResult(
                ok=False,
                provider="openrouter",
                model=self.model,
                scan_id=scan_id,
                date=receipt_date,
                merchant=None,
                currency="HKD",
                total_amount_hkd=None,
                items=[],
                raw={"error": str(exc)},
                error=str(exc),
            )

    def _parse_json_only(self, text: Any) -> Dict[str, Any]:
        if isinstance(text, dict):
            return text
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("empty_model_output")
        # Strip common markdown fences
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)

    def _normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        items_in = payload.get("items") or []
        items: List[Dict[str, Any]] = []
        for it in items_in:
            name = str((it or {}).get("item_name") or "").strip()
            if not name:
                continue
            qty = int((it or {}).get("quantity") or 1)
            unit = (it or {}).get("unit_price_hkd")
            sub = (it or {}).get("subtotal_hkd")
            conf = (it or {}).get("ai_confidence")
            items.append(
                {
                    "item_name": name[:240],
                    "quantity": max(qty, 1),
                    "unit_price_hkd": int(unit) if unit is not None else None,
                    "subtotal_hkd": int(sub) if sub is not None else None,
                    "ai_confidence": float(conf) if conf is not None else None,
                }
            )

        d = payload.get("date")
        if isinstance(d, str) and len(d) >= 10:
            d = d[:10]
        elif d is not None:
            d = None

        cur = str(payload.get("currency") or "HKD").upper().strip() or "HKD"
        total = payload.get("total_amount_hkd")
        total_amount_hkd = int(total) if total is not None else None

        merch = payload.get("merchant")
        merchant = str(merch).strip()[:240] if merch else None

        return {
            "date": d,
            "merchant": merchant,
            "currency": cur,
            "total_amount_hkd": total_amount_hkd,
            "items": items,
        }
