"""Tests for FinanceAgent payout branch, AI router fallback, and default message."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.memory_store import MemoryStore
from app.agents.finance_agent import FinanceAgent


def test_finance_agent_profit() -> None:
    memory = MemoryStore()
    agent = FinanceAgent(memory_store=memory)
    response = agent.handle_message("user", "profit?")
    assert "盈利" in response or "HKD" in response
    entries = memory.search_memory(namespace_prefix=("buyeros", "finance"), memory_key="profit")
    assert entries


def test_finance_agent_payout() -> None:
    memory = MemoryStore()
    agent = FinanceAgent(memory_store=memory)
    response = agent.handle_message("user", "payout schedule")
    assert "出糧" in response or "payout" in response.lower() or "5" in response


def test_finance_agent_payout_in_chinese() -> None:
    memory = MemoryStore()
    agent = FinanceAgent(memory_store=memory)
    response = agent.handle_message("user", "結算")
    assert "出糧" in response or "結算" in response


def test_finance_agent_stores_payout_in_memory() -> None:
    memory = MemoryStore()
    agent = FinanceAgent(memory_store=memory)
    agent.handle_message("user", "payout")
    entries = memory.search_memory(namespace_prefix=("buyeros", "finance"), memory_key="payout")
    assert entries


def test_finance_agent_ai_router_fallback() -> None:
    memory = MemoryStore()
    ai_router = MagicMock()
    ai_router.route.return_value = "AI handled general finance question."
    agent = FinanceAgent(memory_store=memory, ai_router=ai_router)
    # Message without profit/payout keywords → routes to AI router
    response = agent.handle_message("user", "should we do quarterly tax filing?")
    ai_router.route.assert_called_once_with(role="finance", prompt="should we do quarterly tax filing?")
    assert response == "AI handled general finance question."


def test_finance_agent_ai_router_error_falls_through() -> None:
    memory = MemoryStore()
    ai_router = MagicMock()
    ai_router.route.side_effect = Exception("Router down")
    agent = FinanceAgent(memory_store=memory, ai_router=ai_router)
    response = agent.handle_message("user", "should we do quarterly tax filing?")
    assert "已收到" in response


def test_finance_agent_default_message() -> None:
    memory = MemoryStore()
    agent = FinanceAgent(memory_store=memory)
    response = agent.handle_message("user", "hello world")
    assert "已收到" in response
