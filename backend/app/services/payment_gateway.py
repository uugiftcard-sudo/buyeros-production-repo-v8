"""Custom REST payment gateway compatibility client."""

from __future__ import annotations

from typing import Any, Optional

import requests

from .adapters.custom_adapter import CustomRestAdapter


class PaymentGatewayClient(CustomRestAdapter):
    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        if not self.configured():
            return {
                "ok": False,
                "provider": "local_fallback",
                "status": "not_configured",
                "message": f"交易 {transaction_id} 退款網關未配置，已記錄待處理。",
            }
        result = super().refund(transaction_id, amount=amount, reason=reason)
        return {"ok": True, **result, "provider": "remote_gateway"}
