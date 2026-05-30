"""PayPal refund adapter."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, Optional

import requests

from .base_adapter import PaymentAdapter


class PayPalAdapter(PaymentAdapter):
    """Refund via PayPal Orders / Captures API.

    Docs: https://developer.paypal.com/docs/api-basics/#live-endpoints
    """

    SANDBOX_AUTH_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    LIVE_AUTH_URL = "https://api-m.paypal.com/v1/oauth2/token"

    SANDBOX_API_URL = "https://api-m.sandbox.paypal.com"
    LIVE_API_URL = "https://api-m.paypal.com"

    def __init__(self) -> None:
        self.client_id = os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "")
        self.mode = os.getenv("PAYPAL_MODE", "sandbox")

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _base_url(self) -> str:
        return self.SANDBOX_API_URL if self.mode == "sandbox" else self.LIVE_API_URL

    def _auth_url(self) -> str:
        return self.SANDBOX_AUTH_URL if self.mode == "sandbox" else self.LIVE_AUTH_URL

    def _get_access_token(self) -> str:
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        response = requests.post(
            self._auth_url(),
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials",
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        # PayPal uses capture_id as the transaction identifier for refunds
        capture_id = transaction_id
        access_token = self._get_access_token()
        url = f"{self._base_url()}/v2/payments/captures/{capture_id}/refund"

        payload: Dict[str, Any] = {}
        if amount is not None:
            payload["amount"] = {"value": f"{amount:.2f}", "currency_code": "HKD"}
        if reason:
            payload["note_to_payer"] = reason

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload if payload else None,
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "provider": "paypal",
            "status": data.get("status", "COMPLETED"),
            "refund_id": data.get("id", ""),
            "amount": data.get("amount", {}).get("value", amount),
            "currency": data.get("amount", {}).get("currency_code", "HKD"),
            "message": f"PayPal 退款成功，退款編號 {data.get('id', '')}。",
            "raw": data,
        }
