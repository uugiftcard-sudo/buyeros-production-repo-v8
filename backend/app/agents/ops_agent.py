"""Operations agent.

The operations agent handles tasks related to order management such as
processing refunds, viewing orders and extracting text from receipts via OCR,
and looking up buyer profiles.  It delegates specialised actions to tools
registered in the ``ToolRegistry`` and services injected at construction.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from ..registry import ToolRegistry
from ..memory_store import MemoryStore


logger = logging.getLogger(__name__)


class OpsAgent:
    """Agent responsible for operations: refunds, OCR, orders, buyers."""

    def __init__(
        self,
        *,
        memory_store: MemoryStore,
        tool_registry: Optional[ToolRegistry] = None,
        ai_router: Optional[Any] = None,
        orders_service: Optional[Any] = None,
        buyers_service: Optional[Any] = None,
    ) -> None:
        self.memory = memory_store
        self.tools = tool_registry
        self.ai_router = ai_router
        self.orders_service = orders_service
        self.buyers_service = buyers_service

    def handle_message(self, user_id: str, text: str) -> str:
        """Handle an ops message and return a response string.

        Keyword routing:
        - refund / 退款 / ref + 3+ digit number  → process_refund tool
        - ocr / 文字識別 + image URL              → extract_text tool
        - order / 訂單 / 查單 + order number    → OrdersService
        - buyer / 買家 / 客人 / customer          → BuyersService
        - fallback                                → AI router or default message
        """
        lower = text.lower()

        # ── Refund ───────────────────────────────────────────────────────
        if any(kw in lower for kw in ["refund", "退款", "ref"]):
            return self._handle_refund(text)

        # ── OCR ─────────────────────────────────────────────────────────
        if any(kw in lower for kw in ["ocr", "文字識別"]):
            return self._handle_ocr(text)

        # ── Order lookup ─────────────────────────────────────────────────
        if any(kw in lower for kw in ["order", "訂單", "查單"]):
            return self._handle_order(text)

        # ── Buyer lookup ────────────────────────────────────────────────
        if any(kw in lower for kw in ["buyer", "買家", "客人", "customer"]):
            return self._handle_buyer(text)

        # ── Fallback ────────────────────────────────────────────────────
        if self.ai_router:
            try:
                return self.ai_router.route(role="ops", prompt=text)
            except Exception as exc:
                logger.error("AI router error: %s", exc)

        return (
            "已收到，請提供更多資訊，例如：\n"
            "• 退款 123456\n"
            "• ocr https://...\n"
            "• 訂單 ABC123DEF\n"
            "• 買家 CUST001"
        )

    # ── Handlers ────────────────────────────────────────────────────────────

    def _handle_refund(self, text: str) -> str:
        match = re.search(r"(\d{3,})", text)
        if not match:
            return "請提供交易編號，例如：退款 123456"
        txn_id = match.group(1)

        if self.tools and self.tools.has_tool("refund"):
            result = self.tools.call("refund", {"transaction_id": txn_id})
        else:
            result = f"交易 {txn_id} 已處理退款，請耐心等待銀行確認。"

        self.memory.save_memory(
            ["buyeros", "refunds"],
            txn_id,
            {"result": result, "provider": "ops_agent", "project_id": "cloth", "project": "cloth"},
            created_by="ops_agent",
        )
        return result

    def _handle_ocr(self, text: str) -> str:
        url_match = re.search(r"(https?://\S+)", text)
        image_url = url_match.group(1) if url_match else ""

        if self.tools and self.tools.has_tool("ocr"):
            result = self.tools.call("ocr", {"image_url": image_url})
        else:
            result = "暫未設置 OCR 工具。"

        return result

    def _handle_order(self, text: str) -> str:
        if not self.orders_service:
            return "暫未設置訂單服務。"

        # Try to extract an order number (alphanumeric, 6+ chars)
        order_match = re.search(r"\b([A-Z0-9]{6,})\b", text.upper())
        if order_match:
            order_id = order_match.group(1)
            try:
                order = self.orders_service.get_order(order_id)
                if "error" in order:
                    return f"查詢訂單 {order_id} 失敗：{order.get('message', '未知錯誤')}"

                # Persist to memory
                self.memory.save_memory(
                    ["buyeros", "orders"],
                    order_id,
                    order,
                    created_by="ops_agent",
                )

                # Persist buyer reference if available
                customer_id = str(order.get("customer_id", ""))
                if customer_id:
                    self.memory.save_memory(
                        ["buyeros", "buyers"],
                        customer_id,
                        {"source": "order_lookup", "order_id": order_id},
                        created_by="ops_agent",
                    )

                lines = [
                    f"訂單 #{order.get('order_number', order_id)}",
                    f"狀態：{order.get('financial_status', 'N/A')}",
                    f"總額：{order.get('total_price', 'N/A')} {order.get('currency', '')}",
                    f"客戶：{order.get('customer_email', 'N/A')}",
                    f"建立時間：{order.get('created_at', 'N/A')}",
                ]
                return "\n".join(lines)
            except Exception as exc:
                logger.error("Order lookup failed for %s: %s", order_id, exc)
                return f"查詢訂單 {order_id} 時發生錯誤，請稍後重試。"

        # No order ID in message — return recent orders list
        try:
            orders = self.orders_service.list_orders(limit=5)
            if not orders:
                return "暫無最近訂單記錄。"
            lines = ["最近 5 筆訂單："]
            for o in orders:
                lines.append(
                    f"#{o.get('order_number', o.get('order_id', '?'))}"
                    f"｜ {o.get('total_price', '?')} "
                    f"｜ {o.get('financial_status', '?')} "
                    f"｜ {str(o.get('created_at', ''))[:10]}"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.error("List orders failed: %s", exc)
            return "暫時無法取得訂單列表，請稍後重試。"

    def _handle_buyer(self, text: str) -> str:
        if not self.buyers_service:
            return "暫未設置買家服務。"

        # Try to extract a customer ID (numeric or alphanumeric, 4+ chars)
        cust_match = re.search(r"\b([A-Z0-9]{4,})\b", text.upper())
        if cust_match:
            customer_id = cust_match.group(1)
            try:
                buyer = self.buyers_service.get_customer(customer_id)
                if "error" in buyer:
                    return f"查詢買家 {customer_id} 失敗：{buyer.get('message', '未知錯誤')}"

                self.memory.save_memory(
                    ["buyeros", "buyers"],
                    customer_id,
                    buyer,
                    created_by="ops_agent",
                )

                name = " ".join(
                    x for x in [buyer.get("first_name", ""), buyer.get("last_name", "")] if x
                ) or "N/A"
                lines = [
                    f"買家 #{buyer.get('customer_id', customer_id)}",
                    f"姓名：{name}",
                    f"電郵：{buyer.get('email', 'N/A')}",
                    f"電話：{buyer.get('phone', 'N/A')}",
                    f"訂單總數：{buyer.get('orders_count', 'N/A')}",
                    f"總消費：{buyer.get('total_spent', 'N/A')}",
                ]
                return "\n".join(lines)
            except Exception as exc:
                logger.error("Buyer lookup failed for %s: %s", customer_id, exc)
                return f"查詢買家 {customer_id} 時發生錯誤，請稍後重試。"

        # No customer ID — return recent buyers
        try:
            customers = self.buyers_service.list_customers(limit=5)
            if not customers:
                return "暫無買家記錄。"
            lines = ["最近 5 位買家："]
            for c in customers:
                lines.append(
                    f"{c.get('name', c.get('customer_id', '?'))}"
                    f"｜ {c.get('email', '?')} "
                    f"｜ 訂單 {c.get('orders_count', 0)} 筆"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.error("List customers failed: %s", exc)
            return "暫時無法取得買家列表，請稍後重試。"
