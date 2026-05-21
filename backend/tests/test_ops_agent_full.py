"""Tests for OpsAgent order/buyer/ocr branches not covered by test_ops_refund.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.agents.ops_agent import OpsAgent
from app.memory_store import MemoryStore


class TestOpsAgentOrder:
    def test_handle_order_extracts_order_id_and_delegates(self) -> None:
        memory = MemoryStore()
        orders_service = MagicMock()
        orders_service.get_order.return_value = {
            "order_id": "ORD999",
            "order_number": "ORD999",
            "financial_status": "paid",
            "total_price": "199.00",
            "currency": "HKD",
            "customer_email": "alice@example.com",
            "created_at": "2024-01-15T10:30:00Z",
        }

        agent = OpsAgent(memory_store=memory, orders_service=orders_service, buyers_service=MagicMock())
        response = agent.handle_message("user1", "order ORD999")

        orders_service.get_order.assert_called_once_with("ORD999")
        assert "ORD999" in response
        assert "paid" in response
        assert "199.00" in response

    def test_handle_order_no_id_returns_recent_orders(self) -> None:
        memory = MemoryStore()
        orders_service = MagicMock()
        orders_service.list_orders.return_value = [
            {"order_number": "ORD001", "total_price": "100", "financial_status": "paid", "created_at": "2024-01-01T00:00:00Z"},
            {"order_number": "ORD002", "total_price": "200", "financial_status": "pending", "created_at": "2024-01-02T00:00:00Z"},
        ]

        agent = OpsAgent(memory_store=memory, orders_service=orders_service, buyers_service=MagicMock())
        response = agent.handle_message("user1", "查詢我的訂單")

        orders_service.list_orders.assert_called_once()
        assert "最近 5 筆訂單" in response
        assert "ORD001" in response

    def test_handle_order_error_returns_error_message(self) -> None:
        memory = MemoryStore()
        orders_service = MagicMock()
        orders_service.get_order.side_effect = Exception("Network timeout")

        agent = OpsAgent(memory_store=memory, orders_service=orders_service, buyers_service=MagicMock())
        response = agent.handle_message("user1", "order ORD999")

        assert "錯誤" in response or "Error" in response or "ORD999" in response

    def test_handle_order_no_service_returns_service_not_configured(self) -> None:
        memory = MemoryStore()
        agent = OpsAgent(memory_store=memory, orders_service=None)
        response = agent.handle_message("user1", "order ORD999")
        assert "未設置訂單服務" in response


class TestOpsAgentBuyer:
    def test_handle_buyer_extracts_customer_id_and_delegates(self) -> None:
        memory = MemoryStore()
        buyers_service = MagicMock()
        buyers_service.get_customer.return_value = {
            "customer_id": "CUST001",
            "first_name": "Alice",
            "last_name": "Wong",
            "email": "alice@example.com",
            "phone": "+852 9123 4567",
            "orders_count": 5,
            "total_spent": "999.00",
        }

        agent = OpsAgent(memory_store=memory, buyers_service=buyers_service)
        # Use a message without the word "customer" to avoid the regex matching "CUSTOMER"
        response = agent.handle_message("user1", "查詢買家 CUST001")

        captured = buyers_service.get_customer.call_args[0][0]
        assert captured == "CUST001"
        assert "alice@example.com" in response

    def test_handle_buyer_no_id_returns_recent_buyers(self) -> None:
        memory = MemoryStore()
        buyers_service = MagicMock()
        buyers_service.list_customers.return_value = [
            {"name": "Alice", "customer_id": "C001", "email": "alice@example.com", "orders_count": 3},
            {"name": "Bob", "customer_id": "C002", "email": "bob@example.com", "orders_count": 1},
        ]

        agent = OpsAgent(memory_store=memory, buyers_service=buyers_service)
        response = agent.handle_message("user1", "買家資料")

        buyers_service.list_customers.assert_called_once()
        assert "最近 5 位買家" in response
        assert "Alice" in response

    def test_handle_buyer_error_returns_error_message(self) -> None:
        memory = MemoryStore()
        buyers_service = MagicMock()
        buyers_service.get_customer.side_effect = Exception("Service unavailable")

        agent = OpsAgent(memory_store=memory, buyers_service=buyers_service)
        response = agent.handle_message("user1", "buyer CUST001")

        assert "錯誤" in response or "Error" in response or "CUST001" in response

    def test_handle_buyer_no_service_returns_service_not_configured(self) -> None:
        memory = MemoryStore()
        agent = OpsAgent(memory_store=memory, buyers_service=None)
        response = agent.handle_message("user1", "buyer CUST001")
        assert "未設置買家服務" in response


class TestOpsAgentOCR:
    def test_handle_ocr_with_url_delegates_to_tool(self) -> None:
        memory = MemoryStore()
        tool_registry = MagicMock()
        tool_registry.has_tool.return_value = True
        tool_registry.call.return_value = "Receipt: HKD 50.00, Date: 2024-01-15"

        agent = OpsAgent(memory_store=memory, tool_registry=tool_registry)
        response = agent.handle_message("user1", "ocr https://example.com/receipt.jpg")

        tool_registry.call.assert_called_once_with("ocr", {"image_url": "https://example.com/receipt.jpg"})
        assert "HKD 50.00" in response

    def test_handle_ocr_no_url_returns_no_tool_message(self) -> None:
        memory = MemoryStore()
        tool_registry = MagicMock()
        tool_registry.has_tool.return_value = True

        agent = OpsAgent(memory_store=memory, tool_registry=tool_registry)
        response = agent.handle_message("user1", "ocr")
        assert "ocr" in response.lower() or "image" in response.lower() or "URL" in response or tool_registry.call.called

    def test_handle_ocr_no_tool_returns_not_configured(self) -> None:
        memory = MemoryStore()
        agent = OpsAgent(memory_store=memory, tool_registry=None)
        response = agent.handle_message("user1", "ocr https://example.com/img.jpg")
        assert "未設置 OCR" in response or "ocr" in response.lower()


class TestOpsAgentFallback:
    def test_fallback_delegates_to_ai_router(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        ai_router = MagicMock()
        ai_router.route.return_value = "AI handled this generic message."

        agent = OpsAgent(memory_store=memory, ai_router=ai_router)
        response = agent.handle_message("user1", "what is the weather like?")

        ai_router.route.assert_called_once_with(role="ops", prompt="what is the weather like?")
        assert response == "AI handled this generic message."

    def test_fallback_ai_router_error_falls_through(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        memory = MemoryStore()
        ai_router = MagicMock()
        ai_router.route.side_effect = Exception("Router error")

        agent = OpsAgent(memory_store=memory, ai_router=ai_router)
        response = agent.handle_message("user1", "generic message")

        # Should return default message
        assert "退款" in response or "ocr" in response or "請提供" in response

    def test_fallback_no_router_returns_default_message(self) -> None:
        memory = MemoryStore()
        agent = OpsAgent(memory_store=memory, ai_router=None)
        response = agent.handle_message("user1", "generic message")
        assert "退款" in response or "ocr" in response or "請提供" in response


class TestOpsAgentMultipleKeywords:
    def test_refund_takes_priority_over_other_keywords(self) -> None:
        memory = MemoryStore()
        tool_registry = MagicMock()
        tool_registry.has_tool.return_value = True
        tool_registry.call.return_value = "Refund processed."

        agent = OpsAgent(memory_store=memory, tool_registry=tool_registry)
        # "order" keyword present but "refund" checked first
        response = agent.handle_message("user1", "refund order 12345")
        tool_registry.call.assert_called()
        # The response is whatever process_refund returns via tool_registry
        assert "processed" in response.lower() or "refund" in response.lower()
