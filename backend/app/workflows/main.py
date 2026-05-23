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
from fastapi.middleware.cors import CORSMiddleware
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
    AlertsRequest,
    ApprovalRequest,
    CloseCycleRequest,
    ContextSearchRequest,
    ContextSummarizeRequest,
    ContextWriteRequest,
    DailyReportRequest,
    DispatchPlanRequest,
    MemoryTimelineRequest,
    OcrPostingRequest,
    PromoCampaignRequest,
    PromoEventRequest,
    ProjectUpsertRequest,
    ReportCreateRequest,
    ReportExportRequest,
    ReconcileRequest,
    RetryRequest,
    SubtaskRunRequest,
    TaskDispatchRequest,
    TaskCreateRequest,
    TaskRunAllRequest,
    TaskRunRequest,
    TaskStatusRequest,
)
from ..runtime.session_store import RedisSessionStore
from ..security import require_api_key
from ..services.business_automation import BusinessAutomationService
from ..services.memory_timeline_service import MemoryTimelineService
from ..services.ops_status_service import OpsStatusService
from ..services.promo_service import PromoService
from ..services.project_registry_service import ProjectRegistryService
from ..services.reporting_service import ReportingService
from ..services.task_board_service import TaskBoardService
from ..services.task_dispatcher_service import TaskDispatcherService
from ..workflows.buyeros_graph import BuyerOSGraphWorkflow

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""
    app = FastAPI(title="BuyerOS API")
    cors_origins = [
        origin.strip()
        for origin in os.getenv("BUYEROS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Setup memory store (Supabase if env vars present, otherwise memory)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    memory_store = MemoryStore(supabase_url=supabase_url, supabase_key=supabase_key)

    # Setup AI router
    ai_router = AIModelRouter()
    context_hub = ContextHub(memory_store)
    session_store = RedisSessionStore(os.getenv("REDIS_URL"))
    audit_logger = AuditLogger(memory_store)
    reporting_service = ReportingService(memory_store)
    promo_service = PromoService(memory_store)
    task_board_service = TaskBoardService(memory_store)
    project_registry = ProjectRegistryService(memory_store)
    timeline_service = MemoryTimelineService(memory_store)
    ops_status_service = OpsStatusService()

    # Setup tool registry and register tools
    tool_registry = ToolRegistry()
    tool_registry.register("refund", process_refund)
    tool_registry.register("ocr", extract_text)

    # Setup agents
    from ..services.orders_service import OrdersService
    from ..services.buyers_service import BuyersService
    orders_service = OrdersService()
    buyers_service = BuyersService()
    business_automation = BusinessAutomationService(memory_store, orders_service=orders_service)

    ops_agent = OpsAgent(
        memory_store=memory_store,
        tool_registry=tool_registry,
        ai_router=ai_router,
        orders_service=orders_service,
        buyers_service=buyers_service,
    )
    finance_agent = FinanceAgent(memory_store=memory_store, tool_registry=tool_registry, ai_router=ai_router)
    supervisor = SupervisorAgent(memory_store=memory_store, ops_agent=ops_agent, finance_agent=finance_agent)
    provider_registry = ProviderRegistry(context_hub=context_hub)
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

    dispatcher_service = TaskDispatcherService(
        memory_store=memory_store,
        task_board=task_board_service,
        projects=project_registry,
        providers=provider_registry,
        context_hub=context_hub,
        ops_agent=ops_agent,
        finance_agent=finance_agent,
    )
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
    app.state.business_automation = business_automation
    app.state.reporting_service = reporting_service
    app.state.promo_service = promo_service
    app.state.task_board_service = task_board_service
    app.state.project_registry = project_registry
    app.state.timeline_service = timeline_service
    app.state.dispatcher_service = dispatcher_service
    app.state.ops_status_service = ops_status_service
    app.state.orders_service = orders_service
    app.state.buyers_service = buyers_service

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
        if not items:
            # Backward-compatible fallback for historical rows where callers
            # keyed memory on session_id but failed to persist content.session_id.
            fallback_items = context_hub.memory_store.search_memory(
                namespace_prefix=("buyeros", "ai_context"),
                memory_key=session_id,
                limit=50,
            )
            if fallback_items:
                items = fallback_items
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

    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Operator-friendly root endpoint."""
        return {
            "ok": True,
            "service": "BuyerOS API",
            "ui": "http://127.0.0.1:3000",
            "health": "/health/ready",
            "ping": "/ping",
            "docs": "/docs",
        }

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

    @app.get("/ai-team/status", dependencies=[Depends(require_api_key)])
    async def ai_team_status() -> Dict[str, Any]:
        """Return AI provider readiness for the operator UI."""
        return {"ok": True, "providers": provider_registry.status()}

    @app.get("/projects", dependencies=[Depends(require_api_key)])
    async def projects_list(limit: int = 50) -> Dict[str, Any]:
        """List registered projects (core + external)."""
        return project_registry.list_projects(limit=min(max(limit, 1), 200))

    @app.post("/projects", dependencies=[Depends(require_api_key)])
    async def projects_upsert(payload: ProjectUpsertRequest) -> Dict[str, Any]:
        """Create or update a project entry."""
        return project_registry.upsert_project(project_id=payload.project_id, content=payload.model_dump(), created_by="api")

    @app.post("/memory/timeline", dependencies=[Depends(require_api_key)])
    async def memory_timeline(payload: MemoryTimelineRequest) -> Dict[str, Any]:
        """Query a merged timeline across key namespaces."""
        return timeline_service.timeline(
            project_id=payload.project_id,
            session_id=payload.session_id,
            query=payload.query,
            limit=payload.limit,
        )

    @app.get("/audit/search", dependencies=[Depends(require_api_key)])
    async def audit_search(limit: int = 20) -> Dict[str, Any]:
        """Return recent audit events."""
        items = memory_store.search_memory(namespace_prefix=("buyeros", "audit"), limit=min(max(limit, 1), 100))
        return {"ok": True, "items": items}

    @app.get("/ops/status", dependencies=[Depends(require_api_key)])
    async def ops_status() -> Dict[str, Any]:
        """Return latest backup, rollback, failover, and smoke summaries."""
        return ops_status_service.status()

    @app.get("/cloth/orders", dependencies=[Depends(require_api_key)])
    async def cloth_orders(customer_id: str | None = None, limit: int = 10) -> Dict[str, Any]:
        """List CLOTH orders from the configured e-commerce provider."""
        items = orders_service.list_orders(customer_id=customer_id, limit=min(max(limit, 1), 100))
        for item in items:
            order_key = str(item.get("order_id") or item.get("id") or item.get("order_number") or "")
            if order_key:
                memory_store.save_memory(["buyeros", "orders"], order_key, {"project_id": "cloth", **item}, created_by="orders_service")
        return {"ok": True, "items": items, "configured": orders_service.configured()}

    @app.get("/cloth/orders/{order_id}", dependencies=[Depends(require_api_key)])
    async def cloth_order_get(order_id: str) -> Dict[str, Any]:
        """Return one CLOTH order from the configured e-commerce provider."""
        order = orders_service.get_order(order_id)
        ok = not bool(order.get("error"))
        if ok:
            memory_store.save_memory(["buyeros", "orders"], order_id, {"project_id": "cloth", **order}, created_by="orders_service")
        return {"ok": ok, "order": order, "configured": orders_service.configured()}

    @app.post("/automation/daily-report", dependencies=[Depends(require_api_key)])
    async def automation_daily_report(payload: DailyReportRequest) -> Dict[str, Any]:
        """Create a daily operations report from current BuyerOS memory."""
        result = business_automation.create_daily_report(date=payload.date)
        audit_logger.log(action="automation.daily_report", actor="api", details=result)
        return result

    @app.post("/automation/ocr-posting", dependencies=[Depends(require_api_key)])
    async def automation_ocr_posting(payload: OcrPostingRequest) -> Dict[str, Any]:
        """Create an accounting entry from OCR text."""
        result = business_automation.post_ocr_entry(
            text=payload.text,
            source=payload.source,
            entry_id=payload.entry_id,
        )
        audit_logger.log(action="automation.ocr_posting", actor="api", details=result)
        return result

    @app.post("/automation/reconcile", dependencies=[Depends(require_api_key)])
    async def automation_reconcile(payload: ReconcileRequest) -> Dict[str, Any]:
        """Compare expected and actual totals and create an alert on mismatch."""
        result = business_automation.reconcile_entries(
            expected_total=payload.expected_total,
            actual_total=payload.actual_total,
            reference=payload.reference,
        )
        audit_logger.log(action="automation.reconcile", actor="api", details=result)
        return result

    @app.post("/automation/alerts", dependencies=[Depends(require_api_key)])
    async def automation_alerts(payload: AlertsRequest) -> Dict[str, Any]:
        """Generate anomaly alerts for items above a threshold."""
        result = business_automation.generate_alerts(
            items=[item.model_dump() for item in payload.items],
            threshold=payload.threshold,
        )
        audit_logger.log(action="automation.alerts", actor="api", details=result)
        return result

    @app.post("/automation/approval", dependencies=[Depends(require_api_key)])
    async def automation_approval(payload: ApprovalRequest) -> Dict[str, Any]:
        """Create a manual approval task."""
        result = business_automation.request_approval(
            task_id=payload.task_id,
            reason=payload.reason,
            payload=payload.payload,
        )
        audit_logger.log(action="automation.approval", actor="api", details=result)
        return result

    @app.post("/automation/retry", dependencies=[Depends(require_api_key)])
    async def automation_retry(payload: RetryRequest) -> Dict[str, Any]:
        """Record retry state for an automation task."""
        result = business_automation.record_retry(
            task_id=payload.task_id,
            error=payload.error,
            attempt=payload.attempt,
        )
        audit_logger.log(action="automation.retry", actor="api", details=result)
        return result

    @app.post("/automation/close-cycle", dependencies=[Depends(require_api_key)])
    async def automation_close_cycle(payload: CloseCycleRequest) -> Dict[str, Any]:
        """Run the CLOTH OCR -> reconcile -> alert -> approval/retry -> report flow."""
        result = business_automation.close_cycle(
            ocr_text=payload.ocr_text,
            expected_total=payload.expected_total,
            actual_total=payload.actual_total,
            order_id=payload.order_id,
            image_url=payload.image_url,
            ocr_language=payload.ocr_language,
            reference=payload.reference,
            source=payload.source,
            retry_error=payload.retry_error,
            retry_attempt=payload.retry_attempt,
            high_risk=payload.high_risk,
            date=payload.date,
        )
        audit_logger.log(action="automation.close_cycle", actor="api", details=result)
        return result

    @app.post("/reports/create", dependencies=[Depends(require_api_key)])
    async def reports_create(payload: ReportCreateRequest) -> Dict[str, Any]:
        """Create a buyer report snapshot."""
        result = reporting_service.create_report(period=payload.period, date=payload.date)
        audit_logger.log(action="reports.create", actor="api", details={"period": payload.period, "date": payload.date})
        return result

    @app.get("/reports/history", dependencies=[Depends(require_api_key)])
    async def reports_history(limit: int = 20) -> Dict[str, Any]:
        """Return report history."""
        return reporting_service.history(limit=min(max(limit, 1), 100))

    @app.post("/reports/export", dependencies=[Depends(require_api_key)])
    async def reports_export(payload: ReportExportRequest) -> Dict[str, Any]:
        """Export report history as CSV text."""
        return reporting_service.export_csv(report_id=payload.report_id, limit=payload.limit)

    @app.post("/promo/campaigns", dependencies=[Depends(require_api_key)])
    async def promo_campaigns_create(payload: PromoCampaignRequest) -> Dict[str, Any]:
        """Create an XAU promo campaign."""
        result = promo_service.create_campaign(
            name=payload.name,
            offer=payload.offer,
            channel=payload.channel,
            budget_hkd=payload.budget_hkd,
            utm_source=payload.utm_source,
            utm_campaign=payload.utm_campaign,
        )
        audit_logger.log(action="promo.campaigns.create", actor="api", details=result.get("campaign", {}))
        return result

    @app.get("/promo/campaigns", dependencies=[Depends(require_api_key)])
    async def promo_campaigns_list(limit: int = 20) -> Dict[str, Any]:
        """List XAU promo campaigns."""
        return promo_service.list_campaigns(limit=min(max(limit, 1), 100))

    @app.post("/promo/events", dependencies=[Depends(require_api_key)])
    async def promo_events(payload: PromoEventRequest) -> Dict[str, Any]:
        """Record XAU promo event or conversion."""
        result = promo_service.record_event(
            campaign_id=payload.campaign_id,
            event_type=payload.event_type,
            value_hkd=payload.value_hkd,
            source=payload.source,
            metadata=payload.metadata,
        )
        audit_logger.log(action="promo.events.create", actor="api", details=result.get("event", {}))
        return result

    @app.get("/promo/metrics", dependencies=[Depends(require_api_key)])
    async def promo_metrics(campaign_id: str | None = None) -> Dict[str, Any]:
        """Return XAU promo metrics."""
        return promo_service.metrics(campaign_id=campaign_id)

    @app.post("/tasks", dependencies=[Depends(require_api_key)])
    async def tasks_create(payload: TaskCreateRequest) -> Dict[str, Any]:
        """Create a cross-AI task board item."""
        result = task_board_service.create_task(
            title=payload.title,
            lane=payload.lane,
            owner_provider=payload.owner_provider,
            priority=payload.priority,
            payload=payload.payload,
        )
        audit_logger.log(action="tasks.create", actor="api", details=result.get("task", {}))
        return result

    @app.get("/tasks", dependencies=[Depends(require_api_key)])
    async def tasks_list(lane: str | None = None, limit: int = 50) -> Dict[str, Any]:
        """List AI company OS task board items."""
        return task_board_service.list_tasks(lane=lane, limit=min(max(limit, 1), 100))

    @app.post("/tasks/{task_id}/status", dependencies=[Depends(require_api_key)])
    async def tasks_status(task_id: str, payload: TaskStatusRequest) -> Dict[str, Any]:
        """Update task status."""
        return task_board_service.update_status(task_id=task_id, status=payload.status, note=payload.note)

    @app.post("/tasks/{task_id}/run", dependencies=[Depends(require_api_key)])
    async def tasks_run(task_id: str, payload: TaskRunRequest) -> Dict[str, Any]:
        """Record a task run result."""
        return task_board_service.run_task(task_id=task_id, result=payload.result, provider=payload.provider)

    @app.get("/tasks/{task_id}", dependencies=[Depends(require_api_key)])
    async def tasks_get(task_id: str) -> Dict[str, Any]:
        """Return a task and recent runs."""
        task = memory_store.search_memory(namespace_prefix=("buyeros", "tasks"), memory_key=task_id, limit=1)
        normalized_task = task_board_service.normalize_task_payload(task[0]) if task else None
        runs = memory_store.search_memory(namespace_prefix=("buyeros", "task_runs"), query=task_id, limit=20)
        for run in runs:
            content = run.get("content")
            if isinstance(content, dict):
                run["content"] = dict(content)
        return {"ok": True, "task": normalized_task, "runs": runs}

    @app.post("/tasks/dispatch", dependencies=[Depends(require_api_key)])
    async def tasks_dispatch(payload: TaskDispatchRequest) -> Dict[str, Any]:
        """Create a task and dispatch it to the provider layer (single-hop)."""
        project = task_board_service.normalize_lane(payload.project)
        created = task_board_service.create_task(
            title=payload.title,
            lane=project,
            owner_provider=payload.preferred_provider or "openai",
            priority="P0",
            payload={"project": project, "task_type": payload.task_type, "prompt": payload.prompt},
        )
        task_id = created["task"]["task_id"]
        task_board_service.update_status(task_id=task_id, status="running", note="dispatched")

        project_meta = project_registry.get_project(project_id=project) or {"project_id": project}
        context = context_hub.search_context(query=payload.prompt, session_id=payload.session_id, limit=8)
        context.insert(
            0,
            {
                "namespace": ["buyeros", "projects"],
                "memory_key": project,
                "content": {
                    "summary": f"Project {project}: {project_meta.get('name','')}",
                    "content": project_meta,
                },
            },
        )
        dispatch_prompt = f"[project={project} task_type={payload.task_type}]\n{payload.prompt}"
        result = provider_registry.run(
            prompt=dispatch_prompt,
            context=context,
            preferred=payload.preferred_provider,
            session_id=payload.session_id or f"dispatch-{task_id}",
            task_id=task_id,
        )
        reply = result.get("reply") or ""
        if result.get("ok"):
            task_board_service.run_task(task_id=task_id, result=reply, provider=str(result.get("provider") or "unknown"))
        else:
            task_board_service.update_status(task_id=task_id, status="blocked", note=str(result.get("error") or "provider_failed"))
        audit_logger.log(
            action="tasks.dispatch",
            actor="api",
            details={"task_id": task_id, "project": project, "task_type": payload.task_type, "provider": result.get("provider"), "ok": bool(result.get("ok"))},
        )
        return {"ok": True, "task_id": task_id, "result": result}

    @app.post("/tasks/dispatch_plan", dependencies=[Depends(require_api_key)])
    async def tasks_dispatch_plan(payload: DispatchPlanRequest) -> Dict[str, Any]:
        """Create a task + deterministic subtask plan (no execution)."""
        result = dispatcher_service.create_plan(
            project=payload.project,
            task_type=payload.task_type,
            title=payload.title,
            prompt=payload.prompt,
            preferred_provider=payload.preferred_provider,
            session_id=payload.session_id,
            max_steps=payload.max_steps,
        )
        audit_logger.log(action="tasks.dispatch_plan", actor="api", details={"task_id": result.get("task_id"), "project": payload.project, "task_type": payload.task_type})
        return result

    @app.get("/tasks/{task_id}/subtasks", dependencies=[Depends(require_api_key)])
    async def tasks_subtasks(task_id: str, limit: int = 50) -> Dict[str, Any]:
        """List subtasks for a task."""
        return dispatcher_service.list_subtasks(task_id=task_id, limit=min(max(limit, 1), 200))

    @app.post("/tasks/{task_id}/subtasks/run", dependencies=[Depends(require_api_key)])
    async def tasks_subtasks_run(task_id: str, payload: SubtaskRunRequest) -> Dict[str, Any]:
        """Run a specific subtask."""
        return dispatcher_service.run_subtask(
            task_id=task_id,
            subtask_id=payload.subtask_id,
            preferred_provider=payload.preferred_provider,
            session_id=payload.session_id or f"task-{task_id}",
        )

    @app.post("/tasks/{task_id}/subtasks/next", dependencies=[Depends(require_api_key)])
    async def tasks_subtasks_next(task_id: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Run next queued subtask."""
        preferred = (payload or {}).get("preferred_provider") if isinstance(payload, dict) else None
        session_id = (payload or {}).get("session_id") if isinstance(payload, dict) else None
        return dispatcher_service.run_next(task_id=task_id, preferred_provider=preferred, session_id=session_id)

    @app.post("/tasks/{task_id}/run_all", dependencies=[Depends(require_api_key)])
    async def tasks_run_all(task_id: str, payload: TaskRunAllRequest) -> Dict[str, Any]:
        """Run queued subtasks sequentially until completed/blocked (no loops)."""
        result = dispatcher_service.run_all(
            task_id=task_id,
            preferred_provider=payload.preferred_provider,
            session_id=payload.session_id,
            max_steps=payload.max_steps,
        )
        audit_logger.log(action="tasks.run_all", actor="api", details={"task_id": task_id, "ok": bool(result.get("ok")), "status": result.get("status")})
        return result

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
            "automation": [
                "daily_report",
                "report_history",
                "report_csv_export",
                "ocr_posting",
                "reconciliation",
                "alerts",
                "approval",
                "retry",
                "close_cycle",
                "cloth_orders",
                "ops_status",
                "xau_promo_campaigns",
                "xau_promo_events",
                "ai_task_board",
            ],
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
