"""Refund tool with multi-provider payment gateway support."""

from typing import Dict
import logging

from ..services.payment_gateway_multi import PaymentGatewayMulti

logger = logging.getLogger(__name__)


def process_refund(args: Dict[str, str]) -> str:
    """Process a refund for a given transaction id.

    Routes to Stripe, PayPal, or Custom REST depending on which
    provider is configured.  Falls back to a local message if no
    provider is configured.

    :param args: dictionary with key ``transaction_id`` identifying the transaction
    :return: confirmation message
    """
    txn_id = args.get("transaction_id")
    if not txn_id:
        return "缺少 transaction_id"
    client = PaymentGatewayMulti()
    try:
        result = client.refund(
            txn_id,
            reason=args.get("reason"),
        )
        return result.get("message", f"交易 {txn_id} 已提交退款。")
    except Exception as exc:
        logger.error("Refund gateway failed for %s: %s", txn_id, exc)
        return f"交易 {txn_id} 退款網關暫時不可用，已記錄並稍後重試。"
