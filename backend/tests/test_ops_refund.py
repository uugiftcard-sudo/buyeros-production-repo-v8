from app.memory_store import MemoryStore
from app.agents.ops_agent import OpsAgent
from app.registry import ToolRegistry
from app.tools.refund import process_refund


def test_ops_agent_refund() -> None:
    memory = MemoryStore()
    tools = ToolRegistry()
    tools.register("refund", process_refund)
    agent = OpsAgent(memory_store=memory, tool_registry=tools)
    response = agent.handle_message("user", "refund 321")
    assert "321" in response
    # memory should contain entry
    entries = memory.search_memory(namespace_prefix=("buyeros", "refunds"), memory_key="321")
    assert entries
    assert "321" in entries[0]["content"]["result"]
