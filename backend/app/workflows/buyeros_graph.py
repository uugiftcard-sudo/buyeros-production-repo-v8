"""BuyerOS supervisor workflow.

The workflow uses LangGraph when it is installed.  The deterministic
fallback keeps local tests and minimal deployments working even when the
optional graph runtime is not available yet.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from ..agents.finance_agent import FinanceAgent
from ..agents.ops_agent import OpsAgent
from ..context.context_hub import ContextHub
from ..context.provider_registry import ProviderRegistry
from ..memory_store import MemoryStore
from ..runtime.session_store import RedisSessionStore
from ..schemas.state import BuyerOSState
from ..trace import trace_ctx

logger = logging.getLogger(__name__)


GRAPH_END: Any = None
StateGraphClass: Any = None
try:  # pragma: no cover - exercised only when langgraph is installed
    from langgraph.graph import END as _GRAPH_END, StateGraph as _StateGraphClass

    GRAPH_END = _GRAPH_END
    StateGraphClass = _StateGraphClass
except Exception:  # pragma: no cover - deterministic fallback is tested
    pass


# ── Intent classification keywords ──────────────────────────────────────────────

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "memory_lookup": ["查交易", "transaction #", "transaction id", "history", "記錄"],
    "ops": [
        "ocr", "文字識別", "receipt", "buyyer", "buyer", "客人", "顧客", "customer",
        # Refund = ops action (process, look up, act on a refund)
        "refund", "退款",
        # Order-related actions
        "order", "訂單", "查單", "查單",
    ],
    "finance": [
        "profit", "盈利", "payout", "出糧", "結算", "commission", "傭金",
        "revenue", "收入", "帳單", "invoice",
    ],
}


def _classify_intent(message: str) -> str:
    """Improved intent classification using weighted keyword matching.

    Priority rules:
      - "refund" / "退款" → ops (always, even with transaction ID)
      - Numeric transaction IDs → memory_lookup (only when no strong keyword match)
      - Finance keywords → finance
      - OCR / buyer keywords → ops
    """
    lower = message.lower().strip()

    # Hard-priority: refund = ops action (not memory lookup)
    if any(kw in lower for kw in _INTENT_KEYWORDS["ops"]) and any(
        kw in lower for kw in ["refund", "退款"]
    ):
        return "ops"

    scores: dict[str, float] = {"memory_lookup": 0.0, "ops": 0.0, "finance": 0.0, "provider": 0.0}

    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            scores[intent] += lower.count(kw.lower())

    # Numeric transaction IDs imply memory lookup (but ops/finance win with keywords)
    if re.search(r"\b\d{3,}\b", lower):
        scores["memory_lookup"] += 1.5

    # Finance + currency amount → finance
    if re.search(r"hk\$?\d+|\$?\d+hkd", lower) and scores["finance"] > 0:
        scores["finance"] += 1.0

    # Return highest-scoring intent (>= 1.0) or fall back to provider
    best_intent = max(scores, key=scores.get)
    if scores[best_intent] >= 1.0:
        return best_intent
    return "provider"


class BuyerOSGraphWorkflow:
    """LangGraph-compatible supervisor workflow for BuyerOS."""

    def __init__(
        self,
        *,
        memory_store: MemoryStore,
        context_hub: ContextHub,
        provider_registry: ProviderRegistry,
        ops_agent: OpsAgent,
        finance_agent: FinanceAgent,
        session_store: Optional[RedisSessionStore] = None,
    ) -> None:
        self.memory_store = memory_store
        self.context_hub = context_hub
        self.provider_registry = provider_registry
        self.ops_agent = ops_agent
        self.finance_agent = finance_agent
        self.session_store = session_store
        self._graph = self._build_graph() if StateGraphClass is not None else None

    def handle_message(
        self,
        *,
        user_id: str,
        message: str,
        channel: str = "api",
        provider: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> str:
        start = time.perf_counter()
        ctx = trace_ctx()
        logger.info(
            "workflow.start",
            extra={
                **ctx,
                "user_id": user_id,
                "channel": channel,
                "message_preview": message[:80],
            },
        )

        state: BuyerOSState = {
            "message": message,
            "user_id": user_id,
            "channel": channel,
            "provider": provider,
            "session_id": session_id or user_id,
            "task_id": task_id,
            "memory_hits": [],
            "tool_results": [],
        }
        result = self.run(state)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "workflow.done",
            extra={
                **ctx,
                "intent": result.get("intent"),
                "agent": result.get("agent"),
                "elapsed_ms": elapsed_ms,
            },
        )

        if self.session_store:
            self.session_store.save_state(result.get("session_id"), dict(result))
        return result.get("reply", "BuyerOS 已收到。")

    def run(self, state: BuyerOSState) -> BuyerOSState:
        if self._graph:
            return self._graph.invoke(state)  # type: ignore[no-any-return]
        state = self._classify(state)
        if state["intent"] == "memory_lookup":
            return self._memory_lookup(state)
        if state["intent"] == "ops":
            return self._ops(state)
        if state["intent"] == "finance":
            return self._finance(state)
        return self._provider(state)

    def _build_graph(self) -> Any:  # pragma: no cover - depends on optional runtime
        graph = StateGraphClass(BuyerOSState)
        graph.add_node("classify", self._classify)
        graph.add_node("memory_lookup", self._memory_lookup)
        graph.add_node("ops", self._ops)
        graph.add_node("finance", self._finance)
        graph.add_node("provider", self._provider)
        graph.set_entry_point("classify")
        graph.add_conditional_edges(
            "classify",
            lambda state: state["intent"],
            {
                "memory_lookup": "memory_lookup",
                "ops": "ops",
                "finance": "finance",
                "provider": "provider",
            },
        )
        graph.add_edge("memory_lookup", GRAPH_END)
        graph.add_edge("ops", GRAPH_END)
        graph.add_edge("finance", GRAPH_END)
        graph.add_edge("provider", GRAPH_END)
        return graph.compile()

    def _classify(self, state: BuyerOSState) -> BuyerOSState:
        message = state.get("message", "")
        intent = _classify_intent(message)
        txn_match = re.search(r"\b(\d{3,})\b", message)
        state["transaction_id"] = txn_match.group(1) if txn_match else None
        state["intent"] = intent
        state["agent"] = {
            "memory_lookup": "memory",
            "ops": "ops",
            "finance": "finance",
            "provider": "provider",
        }.get(intent, "provider")

        ctx = trace_ctx()
        logger.debug(
            "workflow.classify",
            extra={**ctx, "intent": intent, "transaction_id": state.get("transaction_id")},
        )
        return state

    def _memory_lookup(self, state: BuyerOSState) -> BuyerOSState:
        txn_id = state.get("transaction_id")
        if not txn_id:
            state["reply"] = "請提供交易編號。"
            return state
        entries = self.memory_store.search_memory(
            namespace_prefix=("buyeros", "refunds"), memory_key=txn_id, limit=1
        )
        state["memory_hits"] = entries
        if entries:
            content = entries[0].get("content") or {}
            state["reply"] = content.get("result") or content.get("summary") or f"找到交易 {txn_id} 的記錄。"
        else:
            context_hits = self.context_hub.search_context(query=txn_id, limit=1)
            state["memory_hits"] = context_hits
            if context_hits:
                content = context_hits[0].get("content") or {}
                state["reply"] = (
                    content.get("summary") or str(content.get("content")) or f"找到交易 {txn_id} 的共用 context。"
                )
            else:
                state["reply"] = f"沒有找到交易 {txn_id} 的記錄。"
        return state

    def _ops(self, state: BuyerOSState) -> BuyerOSState:
        reply = self.ops_agent.handle_message(state.get("user_id", "api"), state.get("message", ""))
        state["reply"] = reply
        self.context_hub.write_context(
            source_provider="openclaw" if state.get("channel") == "openclaw" else "openai",
            content={"reply": reply, "intent": "ops", "message": state.get("message")},
            session_id=state.get("session_id"),
            task_id=state.get("task_id"),
            memory_key=state.get("transaction_id") or state.get("task_id"),
            summary=reply,
            created_by="ops_agent",
        )
        return state

    def _finance(self, state: BuyerOSState) -> BuyerOSState:
        reply = self.finance_agent.handle_message(state.get("user_id", "api"), state.get("message", ""))
        state["reply"] = reply
        self.context_hub.write_context(
            source_provider="openai",
            content={"reply": reply, "intent": "finance", "message": state.get("message")},
            session_id=state.get("session_id"),
            task_id=state.get("task_id"),
            summary=reply,
            created_by="finance_agent",
        )
        return state

    def _provider(self, state: BuyerOSState) -> BuyerOSState:
        message = state.get("message", "")
        context = self.context_hub.search_context(query=message, session_id=state.get("session_id"), limit=5)
        result = self.provider_registry.run(
            prompt=message,
            context=context,
            preferred=state.get("provider"),
            session_id=state.get("session_id"),
            task_id=state.get("task_id"),
        )
        state["provider"] = result.get("provider")
        state["reply"] = result.get("reply", "Provider completed.")
        return state
