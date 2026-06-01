"""Refund tool with multi-provider payment gateway support."""

from typing import Optional
import logging

from ..services.payment_gateway_multi import PaymentGatewayMulti

logger = logging.getLogger(__name__)


def process_refund(*, transaction_id: str, reason: Optional[str] = None) -> str:
    """Process a refund for a given transaction id.

    Routes to Stripe, PayPal, or Custom REST depending on which
    provider is configured. Falls back to a local message if no
    provider is configured.

    :param transaction_id: transaction id to refund
    :param reason: optional refund reason
    :return: confirmation message
    """

    txn_id = str(transaction_id).strip()
    if not txn_id:
        return "缺少 transaction_id"

    client = PaymentGatewayMulti()
    try:
        result = client.refund(txn_id, reason=reason)
        return result.get("message", f"交易 {txn_id} 已提交退款。")
    except Exception as exc:
        logger.error("Refund gateway failed for %s: %s", txn_id, exc)
        return f"交易 {txn_id} 退款網關暫時不可用，已記錄並稍後重試。"
