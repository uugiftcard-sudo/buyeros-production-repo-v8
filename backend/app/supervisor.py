"""Supervisor agent.

The supervisor routes incoming messages to the appropriate domain
agent based on simple heuristics and keyword matching.  It also
handles memory lookup when the message appears to reference a
transaction id without additional context, returning the last
recorded result for that transaction.  This central orchestrator
ensures that agents operate with a shared state via the MemoryStore.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from .memory_store import MemoryStore
from .agents.ops_agent import OpsAgent
from .agents.finance_agent import FinanceAgent

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """Routes messages to OpsAgent or FinanceAgent based on content."""

    def __init__(self, *, memory_store: MemoryStore, ops_agent: OpsAgent, finance_agent: FinanceAgent) -> None:
        self.memory_store = memory_store
        self.ops_agent = ops_agent
        self.finance_agent = finance_agent

    def handle_message(self, user_id: str, text: str) -> str:
        """Determine which agent should handle the message.

        If the message consists solely of a numeric transaction id,
        attempt to fetch the last memory entry for that id.  Otherwise,
        route to OpsAgent or FinanceAgent based on keywords.  Unknown
        content returns a default message.
        """
        lower = text.lower().strip()
        txn_match = re.search(r"\b(\d{3,})\b", lower)
        txn_id = txn_match.group(1) if txn_match else None
        # If message is a bare or follow-up transaction lookup, fetch memory.
        if txn_id and not any(kw in lower for kw in ["refund", "退款", "order", "ocr", "profit", "盈利", "payout", "出糧", "結算"]):
            mem = self.memory_store.search_memory(namespace_prefix=("buyeros", "refunds"), memory_key=txn_id, limit=1)
            if mem:
                content = mem[0].get("content", {})
                return content.get("result", f"找到交易 {txn_id} 的記錄，但無法解析內容。")
            return f"沒有找到交易 {txn_id} 的記錄。"
        # Determine routing based on keywords
        if any(kw in lower for kw in ["refund", "退款", "order", "ocr"]):
            return self.ops_agent.handle_message(user_id, text)
        if any(kw in lower for kw in ["profit", "盈利", "payout", "出糧", "結算"]):
            return self.finance_agent.handle_message(user_id, text)
        # Default: route to ops agent or respond generically
        return self.ops_agent.handle_message(user_id, text)
