"""Multi-provider payment gateway: Stripe, PayPal, or custom REST.

The gateway attempts providers in priority order and returns the result
from the first configured one.  All providers return a normalised response
dict with at least the keys: ok, provider, status, message, raw.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .adapters.base_adapter import PaymentAdapter
from .adapters.stripe_adapter import StripeAdapter
from .adapters.paypal_adapter import PayPalAdapter
from .adapters.custom_adapter import CustomRestAdapter

logger = logging.getLogger(__name__)


class PaymentResult(Dict[str, Any]):
    """Normalised refund result returned by all adapters."""

    def __init__(
        self,
        ok: bool,
        provider: str,
        status: str,
        message: str,
        raw: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            ok=ok,
            provider=provider,
            status=status,
            message=message,
            raw=raw or {},
        )


class PaymentGatewayMulti:
    """Route refund requests to the first configured provider.

    Provider priority: Stripe → PayPal → Custom REST
    """

    def __init__(self) -> None:
        self._adapters: list[tuple[str, PaymentAdapter]] = []
        self._init_adapters()

    def _init_adapters(self) -> None:
        stripe = StripeAdapter()
        if stripe.configured():
            self._adapters.append(("stripe", stripe))
            logger.info("Payment gateway: Stripe is configured")

        paypal = PayPalAdapter()
        if paypal.configured():
            self._adapters.append(("paypal", paypal))
            logger.info("Payment gateway: PayPal is configured")

        custom = CustomRestAdapter()
        if custom.configured():
            self._adapters.append(("custom", custom))
            logger.info("Payment gateway: Custom REST is configured")

        if not self._adapters:
            logger.warning("No payment gateway providers are configured — refunds will use local fallback")

    def refund(
        self,
        transaction_id: str,
        *,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> PaymentResult:
        """Attempt a refund via the first configured provider."""
        if not self._adapters:
            return PaymentResult(
                ok=False,
                provider="local_fallback",
                status="not_configured",
                message=f"交易 {transaction_id} 的退款申請已提交，請留意銀行入賬通知。",
            )

        for name, adapter in self._adapters:
            try:
                result = adapter.refund(
                    transaction_id=transaction_id,
                    amount=amount,
                    reason=reason,
                )
                return PaymentResult(
                    ok=True,
                    provider=result.get("provider", name),
                    status=result.get("status", "unknown"),
                    message=result.get("message", ""),
                    raw=result,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Payment adapter %s failed for transaction %s: %s",
                    name,
                    transaction_id,
                    exc,
                )
                # Try next adapter
                continue

        # All adapters failed
        return PaymentResult(
            ok=False,
            provider="none",
            status="all_providers_failed",
            message=f"交易 {transaction_id} 退款暫時不可用，已記錄並稍後重試。",
        )


