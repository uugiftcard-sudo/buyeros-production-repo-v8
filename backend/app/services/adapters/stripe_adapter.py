"""Stripe refund adapter."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

from .base_adapter import PaymentAdapter


class StripeAdapter(PaymentAdapter):
    """Refund via Stripe API.

    Docs: https://docs.stripe.com/api/refunds
    """

    STRIPE_API_URL = "https://api.stripe.com/v1/refunds"

    def __init__(self) -> None:
        self.api_key = os.getenv("STRIPE_API_KEY", "")
        self.api_version = os.getenv("STRIPE_API_VERSION", "2024-04-10")

    def configured(self) -> bool:
        return bool(self.api_key)

    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, str] = {
            "charge": transaction_id,
            "reason": "requested_by_customer",
        }
        if reason:
            payload["metadata[reason]"] = reason

        response = requests.post(
            self.STRIPE_API_URL,
            auth=(self.api_key, ""),
            data=payload,
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        return {
            "provider": "stripe",
            "status": status,
            "refund_id": data.get("id", ""),
            "amount": data.get("amount", 0) / 100,  # stripe returns cents
            "currency": data.get("currency", "hkd"),
            "message": f"Stripe 退款成功，退款編號 {data.get('id', '')}。",
            "raw": data,
        }
