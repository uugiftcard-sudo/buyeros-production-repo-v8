"""Main FastAPI application for BuyerOS backend.

This module exposes a FastAPI ``create_app`` function that wires up
the memory store, agents, tool registry and supervisor.  It defines a
Webhook endpoint for Telegram and generic endpoints for testing.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ..memory_store import MemoryStore
from ..agents.ops_agent import OpsAgent
from ..agents.finance_agent import FinanceAgent
from ..ai_router import AIModelRouter
from ..audit import AuditLogger
from ..supervisor import SupervisorAgent
from ..registry import AgentRegistry, ToolRegistry
from ..tools.refund import process_refund
from ..tools.ocr import extract_text
from ..context.context_hub import ContextHub
from ..context.provider_registry import ProviderRegistry
from ..context.adapters.claude import ClaudeProviderAdapter
from ..context.adapters.cursor import CursorProviderAdapter
from ..context.adapters.deepseek import DeepSeekProviderAdapter
from ..context.adapters.gemini import GeminiProviderAdapter
from ..context.adapters.grok import GrokProviderAdapter
from ..context.adapters.hermes import HermesProviderAdapter
from ..context.adapters.minimax import MiniMaxProviderAdapter
from ..context.adapters.openai import OpenAIProviderAdapter
from ..context.adapters.openclaw import OpenClawProviderAdapter
from ..context.adapters.openrouter import OpenRouterProviderAdapter
from ..context.adapters.perplexity import PerplexityProviderAdapter
from ..schemas.state import (
    AgentRunRequest,
    ContextSearchRequest,
    ContextSummarizeRequest,
    ContextWriteRequest,
)
from ..runtime.session_store import RedisSessionStore
from ..security import require_api_key
from ..services.orders_service import OrdersService
from ..services.buyers_service import BuyersService
from ..workflows.buyeros_graph import BuyerOSGraphWorkflow

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""
    app = FastAPI(title="BuyerOS API")
    # Setup memory store (Supabase if env vars present, otherwise memory)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    memory_store = MemoryStore(supabase_url=supabase_url, supabase_key=supabase_key)

    # Setup AI router
    ai_router = AIModelRouter()
    context_hub = ContextHub(memory_store)
    session_store = RedisSessionStore(os.getenv("REDIS_URL"))
    audit_logger = AuditLogger(memory_store)

    # Setup tool registry and register tools
    tool_registry = ToolRegistry()
    tool_registry.register("refund", process_refund)
    tool_registry.register("ocr", extract_text)

    # Setup agents
    from ..services.orders_service import OrdersService
    from ..services.buyers_service import BuyersService

    orders_service = OrdersService()
    buyers_service = BuyersService()

    ops_agent = OpsAgent(
        memory_store=memory_store,
        tool_registry=tool_registry,
        ai_router=ai_router,
        orders_service=orders_service,
        buyers_service=buyers_service,
    )
    finance_agent = FinanceAgent(memory_store=memory_store, tool_registry=tool_registry, ai_router=ai_router)
    supervisor = SupervisorAgent(memory_store=memory_store, ops_agent=ops_agent, finance_agent=finance_agent)
    provider_registry = ProviderRegistry()
    for provider in [
        ClaudeProviderAdapter(context_hub=context_hub),
        CursorProviderAdapter(context_hub=context_hub),
        OpenAIProviderAdapter(context_hub=context_hub),
        OpenRouterProviderAdapter(context_hub=context_hub),
        GeminiProviderAdapter(context_hub=context_hub),
        DeepSeekProviderAdapter(context_hub=context_hub),
        MiniMaxProviderAdapter(context_hub=context_hub),
        GrokProviderAdapter(context_hub=context_hub),
        PerplexityProviderAdapter(context_hub=context_hub),
        HermesProviderAdapter(context_hub=context_hub),
        OpenClawProviderAdapter(context_hub=context_hub),
    ]:
        provider_registry.register(provider)
    workflow = BuyerOSGraphWorkflow(
        memory_store=memory_store,
        context_hub=context_hub,
        provider_registry=provider_registry,
        ops_agent=ops_agent,
        finance_agent=finance_agent,
        session_store=session_store,
    )

    # Register to agent registry if needed
    agent_registry = AgentRegistry()
    agent_registry.register("supervisor", supervisor)
    agent_registry.register("ops", ops_agent)
    agent_registry.register("finance", finance_agent)
    app.state.memory_store = memory_store
    app.state.context_hub = context_hub
    app.state.provider_registry = provider_registry
    app.state.workflow = workflow
    app.state.supervisor = supervisor
    app.state.session_store = session_store
    app.state.audit_logger = audit_logger
    app.state.tool_registry = tool_registry
    app.state.agent_registry = agent_registry

    @app.post("/telegram/webhook")
    async def telegram_webhook(request: Request) -> JSONResponse:
        """Handle incoming Telegram updates via webhook.

        This endpoint expects a JSON update from Telegram.  It extracts
        the chat id and message text, passes it to the supervisor and
        sends a reply back to Telegram via the sendMessage API.  The
        Telegram bot token must be provided in the ``TELEGRAM_BOT_TOKEN``
        environment variable.
        """
        expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if expected_secret and request.headers.get("x-telegram-bot-api-secret-token") != expected_secret:
            raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
        try:
            update: Dict[str, Any] = await request.json()
        except Exception as exc:
            logger.error("Failed to parse Telegram update: %s", exc)
            raise HTTPException(status_code=400, detail="Invalid JSON")
        message = update.get("message") or update.get("edited_message")
        if not message:
            return JSONResponse(content={"ok": True})
        chat = message.get("chat")
        chat_id = chat.get("id") if chat else None
        text = message.get("text") or message.get("caption", "")
        if not chat_id or not text:
            return JSONResponse(content={"ok": True})
        user_id = str(chat_id)
        # Delegate to the BuyerOS graph workflow. The legacy supervisor is
        # still available on app.state for tests and compatibility.
        response_text = workflow.handle_message(user_id=user_id, message=text, channel="telegram", session_id=user_id)
        # Send reply via Telegram API
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(send_url, json={"chat_id": chat_id, "text": response_text})
            except Exception as exc:
                logger.error("Failed to send Telegram message: %s", exc)
        return JSONResponse(content={"ok": True})

    @app.post("/context/write", dependencies=[Depends(require_api_key)])
    async def context_write(payload: ContextWriteRequest) -> Dict[str, Any]:
        """Write shared context from any provider/client."""
        item = context_hub.write_context(
            source_provider=payload.source_provider,
            content=payload.content,
            session_id=payload.session_id,
            task_id=payload.task_id,
            memory_key=payload.memory_key,
            summary=payload.summary,
            created_by=payload.created_by,
        )
        audit_logger.log(
            action="context.write",
            actor=payload.created_by or payload.source_provider,
            details={"source_provider": payload.source_provider, "session_id": payload.session_id, "task_id": payload.task_id},
        )
        return {"ok": True, "item": item}

    @app.post("/context/search", dependencies=[Depends(require_api_key)])
    async def context_search(payload: ContextSearchRequest) -> Dict[str, Any]:
        """Search shared provider context."""
        items = context_hub.search_context(
            query=payload.query,
            source_provider=payload.source_provider,
            session_id=payload.session_id,
            limit=payload.limit,
        )
        audit_logger.log(
            action="context.search",
            actor=payload.source_provider or "api",
            details={"query": payload.query, "source_provider": payload.source_provider, "session_id": payload.session_id, "count": len(items)},
        )
        return {"ok": True, "items": items}

    @app.post("/context/summarize", dependencies=[Depends(require_api_key)])
    async def context_summarize(payload: ContextSummarizeRequest) -> Dict[str, Any]:
        """Summarize shared context matching a filter."""
        summary = context_hub.summarize_context(
            query=payload.query,
            source_provider=payload.source_provider,
            session_id=payload.session_id,
            limit=payload.limit,
        )
        audit_logger.log(
            action="context.summarize",
            actor=payload.source_provider or "api",
            details={"query": payload.query, "source_provider": payload.source_provider, "session_id": payload.session_id, "count": summary.get("count")},
        )
        return {"ok": True, **summary}

    @app.get("/context/session/{session_id}", dependencies=[Depends(require_api_key)])
    async def context_session(session_id: str) -> Dict[str, Any]:
        """Return shared context for a specific session."""
        items = context_hub.get_session(session_id)
        audit_logger.log(action="context.session", actor="api", details={"session_id": session_id, "count": len(items)})
        return {"ok": True, "items": items, "last_state": session_store.get_state(session_id)}

    @app.post("/agents/run", dependencies=[Depends(require_api_key)])
    async def agents_run(payload: AgentRunRequest) -> Dict[str, Any]:
        """Run a task through the BuyerOS graph/provider layer."""
        reply = workflow.handle_message(
            user_id=payload.user_id,
            message=payload.prompt,
            channel=payload.channel,
            provider=payload.provider,
            session_id=payload.session_id or payload.user_id,
            task_id=payload.task_id,
        )
        audit_logger.log(
            action="agents.run",
            actor=payload.user_id,
            details={"provider": payload.provider, "channel": payload.channel, "session_id": payload.session_id, "task_id": payload.task_id},
        )
        return {"ok": True, "reply": reply}

    @app.get("/ping")
    async def ping() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready() -> Dict[str, Any]:
        """Readiness check for deployment probes and VPS smoke tests."""
        memory_status = memory_store.status()
        redis_status = session_store.status()
        providers = provider_registry.status()
        return {
            "ok": bool(memory_status.get("ok")),
            "memory": memory_status,
            "redis": redis_status,
            "providers": providers,
            "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            "api_key_required": bool(os.getenv("BUYEROS_API_KEY")),
        }

    @app.get("/providers", dependencies=[Depends(require_api_key)])
    async def providers() -> Dict[str, Any]:
        """List configured provider adapters and model routing defaults."""
        return {"ok": True, "providers": provider_registry.status()}

    @app.get("/audit/search", dependencies=[Depends(require_api_key)])
    async def audit_search(limit: int = 20) -> Dict[str, Any]:
        """Return recent audit events."""
        items = memory_store.search_memory(namespace_prefix=("buyeros", "audit"), limit=min(max(limit, 1), 100))
        return {"ok": True, "items": items}

    @app.get("/system/capabilities", dependencies=[Depends(require_api_key)])
    async def system_capabilities() -> Dict[str, Any]:
        """Return an operator-friendly capability matrix and configuration gaps."""
        required_env = [
            "PUBLIC_BASE_URL",
            "BUYEROS_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_WEBHOOK_SECRET",
            "REDIS_URL",
            "OPENROUTER_API_KEY",
        ]
        missing_env = [key for key in required_env if not os.getenv(key)]
        providers = provider_registry.status()
        provider_models_missing = [item["name"] for item in providers if not item.get("model")]
        return {
            "ok": True,
            "agents": agent_registry.names(),
            "tools": tool_registry.names(),
            "providers": providers,
            "feature_flags": {
                "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
                "api_key_required": bool(os.getenv("BUYEROS_API_KEY")),
                "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
                "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")),
                "redis_configured": bool(os.getenv("REDIS_URL")),
            },
            "gaps": {
                "missing_env": missing_env,
                "provider_models_missing": provider_models_missing,
            },
        }

    return app
