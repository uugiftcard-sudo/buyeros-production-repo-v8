"""Tests for BuyerOSGraphWorkflow nodes in isolation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from app.agents.finance_agent import FinanceAgent
from app.agents.ops_agent import OpsAgent
from app.context.context_hub import ContextHub
from app.context.provider_registry import ProviderRegistry
from app.context.adapters.claude import ClaudeProviderAdapter
from app.memory_store import MemoryStore
from app.schemas.state import BuyerOSState
from app.workflows.buyeros_graph import BuyerOSGraphWorkflow


def make_state(message: str = "hello", user_id: str = "u1") -> BuyerOSState:
    return {
        "message": message,
        "user_id": user_id,
        "channel": "api",
        "provider": None,
        "session_id": "sess-1",
        "task_id": "task-1",
        "memory_hits": [],
        "tool_results": [],
        "intent": "",
        "agent": "",
        "reply": "",
    }


class TestClassifyNode:
    def test_transaction_id_only_routes_to_memory_lookup(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        state = make_state("transaction 991")
        result = workflow._classify(state)
        assert result["intent"] == "memory_lookup"
        assert result["agent"] == "memory"
        assert result["transaction_id"] == "991"

    def test_refund_keyword_routes_to_ops(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        for msg in ["refund 123", "退款 456", "order ORD001"]:
            state = make_state(msg)
            result = workflow._classify(state)
            assert result["intent"] == "ops", f"Failed for: {msg}"
            assert result["agent"] == "ops"

    def test_profit_keyword_routes_to_finance(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        for msg in ["profit this month", "本月盈利", "payout schedule", "出糧"]:
            state = make_state(msg)
            result = workflow._classify(state)
            assert result["intent"] == "finance", f"Failed for: {msg}"
            assert result["agent"] == "finance"

    def test_generic_message_routes_to_provider(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        for msg in ["hello", "what is the status?", "how are you"]:
            state = make_state(msg)
            result = workflow._classify(state)
            assert result["intent"] == "provider", f"Failed for: {msg}"
            assert result["agent"] == "provider"

    def test_ocr_keyword_routes_to_ops(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        state = make_state("ocr https://example.com/receipt.jpg")
        result = workflow._classify(state)
        assert result["intent"] == "ops"
        assert result["transaction_id"] is None


class TestMemoryLookupNode:
    def test_returns_matching_refund_record(self) -> None:
        memory = MemoryStore()
        memory.save_memory(
            ["buyeros", "refunds"],
            "991",
            {"result": "Refund 991 completed."},
            created_by="test",
        )
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        state = make_state("transaction 991")
        state["transaction_id"] = "991"
        result = workflow._memory_lookup(state)
        assert result["memory_hits"]
        assert "991" in result["reply"]

    def test_no_transaction_id_returns_please_provide(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        state = make_state("hello")
        result = workflow._memory_lookup(state)
        assert "reply" in result
        assert "991" not in result["reply"]

    def test_no_record_returns_context_hub_search(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        hub.write_context(
            source_provider="claude",
            session_id="sess-1",
            content={"text": "Transaction 777 handled by Claude."},
            summary="TX 777",
        )
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=hub,
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        state = make_state("transaction 777")
        state["transaction_id"] = "777"
        result = workflow._memory_lookup(state)
        assert "reply" in result

    def test_completely_not_found_returns_not_found_message(self) -> None:
        memory = MemoryStore()
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=ContextHub(memory),
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=MagicMock(),
        )
        state = make_state("transaction 999999")
        state["transaction_id"] = "999999"
        result = workflow._memory_lookup(state)
        assert "reply" in result
        assert "沒有找到" in result["reply"] or "not found" in result["reply"].lower() or "no record" in result["reply"].lower()


class TestOpsNode:
    def test_delegates_to_ops_agent_and_writes_context(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        ops_agent = MagicMock()
        ops_agent.handle_message.return_value = "Refund 123 processed."

        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=hub,
            provider_registry=ProviderRegistry(),
            ops_agent=ops_agent,
            finance_agent=MagicMock(),
        )
        state = make_state("refund 123")
        result = workflow._ops(state)
        assert result["reply"] == "Refund 123 processed."
        ops_agent.handle_message.assert_called_once()
        # Context should be written (verified by presence in hub)
        ctx = hub.search_context(query="Refund 123 processed.")
        assert len(ctx) >= 1


class TestFinanceNode:
    def test_delegates_to_finance_agent_and_writes_context(self) -> None:
        memory = MemoryStore()
        hub = ContextHub(memory)
        finance_agent = MagicMock()
        finance_agent.handle_message.return_value = "Profit this month: HKD 5000."

        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=hub,
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=finance_agent,
        )
        state = make_state("profit this month")
        result = workflow._finance(state)
        assert result["reply"] == "Profit this month: HKD 5000."
        finance_agent.handle_message.assert_called_once()
        ctx = hub.search_context(source_provider="openai", session_id="sess-1")
        assert len(ctx) >= 1


class TestProviderNode:
    def test_delegates_to_provider_registry(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        hub = ContextHub(memory)
        registry = ProviderRegistry()
        registry.register(ClaudeProviderAdapter(context_hub=hub))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Provider handled."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.context.provider_registry.requests.post", return_value=mock_response):
            workflow = BuyerOSGraphWorkflow(
                memory_store=memory,
                context_hub=hub,
                provider_registry=registry,
                ops_agent=MagicMock(),
                finance_agent=MagicMock(),
            )
            state = make_state("hello world")
            result = workflow._provider(state)
            assert "reply" in result
            assert result["provider"] is not None


class TestWorkflowRunIntegration:
    def test_run_routes_refund_to_ops(self) -> None:
        memory = MemoryStore()
        ops_agent = MagicMock()
        ops_agent.handle_message.return_value = "Refund processed."
        hub = ContextHub(memory)
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=hub,
            provider_registry=ProviderRegistry(),
            ops_agent=ops_agent,
            finance_agent=MagicMock(),
        )
        result = workflow.run(make_state("退款 123"))
        assert result["reply"] == "Refund processed."
        assert result["intent"] == "ops"

    def test_run_routes_profit_to_finance(self) -> None:
        memory = MemoryStore()
        finance_agent = MagicMock()
        finance_agent.handle_message.return_value = "HKD 10000 profit."
        hub = ContextHub(memory)
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=hub,
            provider_registry=ProviderRegistry(),
            ops_agent=MagicMock(),
            finance_agent=finance_agent,
        )
        result = workflow.run(make_state("profit this month"))
        assert "HKD" in result["reply"]
        assert result["intent"] == "finance"

    def test_run_saves_session_state_when_store_available(self) -> None:
        memory = MemoryStore()
        session_store = MagicMock()
        hub = ContextHub(memory)
        ops_agent = MagicMock()
        ops_agent.handle_message.return_value = "Handled."
        workflow = BuyerOSGraphWorkflow(
            memory_store=memory,
            context_hub=hub,
            provider_registry=ProviderRegistry(),
            ops_agent=ops_agent,
            finance_agent=MagicMock(),
            session_store=session_store,
        )
        # handle_message calls run() and then save_state() — this is what saves session state
        workflow.handle_message(user_id="u1", message="退款 123")
        session_store.save_state.assert_called_once()
        call_args = session_store.save_state.call_args[0]
        assert "sess-1" in call_args[0]  # session_id contains "sess-1"
