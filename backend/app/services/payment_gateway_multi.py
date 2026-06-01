"""Multi-provider payment gateway router."""

from __future__ import annotations

from typing import Any, Optional

from .adapters.custom_adapter import CustomRestAdapter
from .adapters.paypal_adapter import PayPalAdapter
from .adapters.stripe_adapter import StripeAdapter


class PaymentGatewayMulti:
    def __init__(self) -> None:
        self.adapters = [StripeAdapter(), PayPalAdapter(), CustomRestAdapter()]

    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        configured = [adapter for adapter in self.adapters if adapter.configured()]
        if not configured:
            return {
                "ok": False,
                "provider": "local_fallback",
                "status": "not_configured",
                "message": f"交易 {transaction_id} 退款網關未配置，已記錄待處理。",
            }

        errors: list[str] = []
        for adapter in configured:
            try:
                result = adapter.refund(transaction_id, amount=amount, reason=reason)
            except Exception as exc:
                errors.append(f"{adapter.__class__.__name__}: {exc}")
                continue
            return {"ok": True, **result}

        return {
            "ok": False,
            "provider": "none",
            "status": "all_providers_failed",
            "errors": errors,
            "message": f"交易 {transaction_id} 所有退款網關均失敗，已記錄待重試。",
        }
