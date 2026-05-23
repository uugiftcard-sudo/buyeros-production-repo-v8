from app.agents.finance_agent import FinanceAgent
from app.agents.ops_agent import OpsAgent
from app.context.adapters.claude import ClaudeProviderAdapter
from app.context.adapters.openai import OpenAIProviderAdapter
from app.context.context_hub import ContextHub
from app.context.provider_registry import ProviderRegistry
from app.memory_store import MemoryStore
from app.registry import ToolRegistry
from app.tools.refund import process_refund
from app.workflows.buyeros_graph import BuyerOSGraphWorkflow


def create_workflow() -> BuyerOSGraphWorkflow:
    memory = MemoryStore()
    hub = ContextHub(memory)
    tools = ToolRegistry()
    tools.register("refund", process_refund)
    ops = OpsAgent(memory_store=memory, tool_registry=tools)
    finance = FinanceAgent(memory_store=memory)
    providers = ProviderRegistry()
    providers.register(ClaudeProviderAdapter(context_hub=hub))
    providers.register(OpenAIProviderAdapter(context_hub=hub))
    return BuyerOSGraphWorkflow(
        memory_store=memory,
        context_hub=hub,
        provider_registry=providers,
        ops_agent=ops,
        finance_agent=finance,
    )


def test_graph_refund_then_follow_up_lookup() -> None:
    workflow = create_workflow()

    first = workflow.handle_message(user_id="u1", message="退款 991", channel="test", session_id="s1")
    second = workflow.handle_message(user_id="u1", message="991 點？", channel="test", session_id="s1")

    assert "991" in first
    assert "991" in second


def test_graph_routes_coding_task_to_provider() -> None:
    workflow = create_workflow()

    reply = workflow.handle_message(
        user_id="u1",
        message="please fix this repo bug",
        channel="test",
        session_id="s-code",
    )

    assert "provider key is not configured" in reply.lower()
    assert workflow.context_hub.search_context(source_provider="claude", session_id="s-code")
    assert workflow.context_hub.search_context(source_provider="openai", session_id="s-code")
