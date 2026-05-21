from app.memory_store import MemoryStore
from app.agents.finance_agent import FinanceAgent


def test_finance_agent_profit() -> None:
    memory = MemoryStore()
    agent = FinanceAgent(memory_store=memory)
    response = agent.handle_message("user", "profit?")
    assert "盈利" in response or "HKD" in response
    entries = memory.search_memory(namespace_prefix=("buyeros", "finance"), memory_key="profit")
    assert entries
