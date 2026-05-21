"""Payment gateway integration for refunds."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


class PaymentGatewayClient:
    """Thin HTTP client for external refund gateways.

    Expected provider contract:
    - endpoint: POST {PAYMENT_GATEWAY_BASE_URL}/refunds
    - payload: {"transaction_id": "...", "amount": optional, "reason": optional}
    - auth: bearer token from PAYMENT_GATEWAY_API_KEY
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("PAYMENT_GATEWAY_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("PAYMENT_GATEWAY_API_KEY", "")

    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def refund(self, transaction_id: str, *, amount: Optional[float] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        if not self.configured():
            return {
                "ok": False,
                "provider": "local_fallback",
                "status": "not_configured",
                "message": f"已提交交易 {transaction_id} 的退款申請，請留意銀行入賬通知。",
            }
        payload: Dict[str, Any] = {"transaction_id": transaction_id}
        if amount is not None:
            payload["amount"] = amount
        if reason:
            payload["reason"] = reason
        response = requests.post(
            f"{self.base_url}/refunds",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
        return {
            "ok": True,
            "provider": "remote_gateway",
            "status": data.get("status", "submitted"),
            "message": data.get("message") or f"交易 {transaction_id} 已提交退款。",
            "raw": data,
        }
