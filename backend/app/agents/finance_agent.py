"""Finance agent.

The finance agent handles queries related to profits, payouts and other
financial metrics.  For now it supports simple keywords such as
``profit`` and ``payout``.  If a tool registry contains specialised
finance tools, those will be used; otherwise it returns a canned
response and records the interaction in memory.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..registry import ToolRegistry
from ..memory_store import MemoryStore
from ..services.finance_service import FinanceService
from ..trace import trace_ctx


logger = logging.getLogger(__name__)


def _log_trace(level: int, msg: str, **kwargs: Any) -> None:
    ctx = trace_ctx()
    extra = {k: v for k, v in ctx.items() if v is not None}
    extra.update(kwargs)
    logger.log(level, msg, extra=extra)


class FinanceAgent:
    """Agent responsible for finance tasks such as profit and payout."""

    def __init__(self, *, memory_store: MemoryStore, tool_registry: Optional[ToolRegistry] = None, ai_router: Optional[Any] = None) -> None:
        self.memory = memory_store
        self.tools = tool_registry
        self.ai_router = ai_router
        self.finance_service = FinanceService(memory_store)

    def handle_message(self, user_id: str, text: str) -> str:
        """Handle a finance message and return a response."""
        lower = text.lower()
        if any(kw in lower for kw in ["profit", "盈利", "profit?"]):
            result = self.finance_service.get_profit_summary()
            data = result.get("data", {})
            source_note = data.get("note", "")
            response = f"本月盈利 HKD {data.get('profit_hkd', 'N/A')}（退款 {data.get('refund_count', 0)} 單）"
            if source_note:
                response += f"。{source_note}"
            self.memory.save_memory(["buyeros", "finance"], "profit", {"result": response}, created_by="finance_agent")
            return response
        if any(kw in lower for kw in ["payout", "出糧", "結算"]):
            result = self.finance_service.get_payout_schedule()
            data = result.get("data", {})
            source_note = data.get("note", "")
            response = f"下一次出糧日期為每月 {data.get('next_payout_day', 5)} 號"
            if data.get("currency"):
                response += f"，幣種 {data['currency']}"
            if data.get("status") and data["status"] != "unknown":
                response += f"，狀態 {data['status']}"
            if source_note:
                response += f"。{source_note}"
            self.memory.save_memory(["buyeros", "finance"], "payout", {"result": response}, created_by="finance_agent")
            return response
        # fallback to AI router
        if self.ai_router:
            try:
                return self.ai_router.route(role="finance", prompt=text)
            except Exception as exc:
                _log_trace(logging.ERROR, "ai_router.error", exc=str(exc))
        return "已收到財務查詢，目前僅支援'profit'或'payout'指令。"
