"""Custom REST payment gateway adapter (original PaymentGatewayClient logic)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

from .base_adapter import PaymentAdapter


class CustomRestAdapter(PaymentAdapter):
    """Refund via a custom REST API.

    Expected contract:
    - endpoint: POST {BASE_URL}/refunds
    - payload: {"transaction_id": "...", "amount": optional, "reason": optional}
    - auth: Bearer token from PAYMENT_GATEWAY_API_KEY
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("PAYMENT_GATEWAY_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("PAYMENT_GATEWAY_API_KEY", "")

    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"transaction_id": transaction_id}
        if amount is not None:
            payload["amount"] = amount
        if reason:
            payload["reason"] = reason

        response = requests.post(
            f"{self.base_url}/refunds",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=25,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}

        return {
            "provider": "custom_rest",
            "status": data.get("status", "submitted"),
            "refund_id": data.get("refund_id", transaction_id),
            "message": data.get("message") or f"交易 {transaction_id} 已提交退款。",
            "raw": data,
        }
