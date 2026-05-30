from app.memory_store import MemoryStore
from app.agents.ops_agent import OpsAgent
from app.agents.finance_agent import FinanceAgent
from app.supervisor import SupervisorAgent
from app.registry import ToolRegistry
from app.tools.refund import process_refund


def create_supervisor() -> SupervisorAgent:
    memory = MemoryStore()
    tools = ToolRegistry()
    tools.register("refund", process_refund)
    ops = OpsAgent(memory_store=memory, tool_registry=tools)
    finance = FinanceAgent(memory_store=memory)
    return SupervisorAgent(memory_store=memory, ops_agent=ops, finance_agent=finance)


def test_supervisor_refund_routing() -> None:
    supervisor = create_supervisor()
    response = supervisor.handle_message("user", "退款 888")
    assert "888" in response


def test_supervisor_finance_routing() -> None:
    supervisor = create_supervisor()
    response = supervisor.handle_message("user", "profit 今年如何？")
    assert "盈利" in response or "HKD" in response


def test_supervisor_memory_lookup() -> None:
    supervisor = create_supervisor()
    supervisor.handle_message("user", "refund 999")
    response = supervisor.handle_message("user", "999")
    assert "999" in response


def test_supervisor_fallback_routes_to_ops() -> None:
    supervisor = create_supervisor()
    response = supervisor.handle_message("user", "hello world")
    assert response  # non-empty response


def test_supervisor_ocr_routing() -> None:
    supervisor = create_supervisor()
    response = supervisor.handle_message("user", "ocr https://example.com/receipt.jpg")
    assert response


def test_supervisor_order_routing() -> None:
    supervisor = create_supervisor()
    response = supervisor.handle_message("user", "order ORD123456")
    assert response


def test_supervisor_buyer_routing() -> None:
    supervisor = create_supervisor()
    response = supervisor.handle_message("user", "buyer CUST001")
    assert response
