"""Main FastAPI application for BuyerOS backend.

This module exposes a FastAPI ``create_app`` function that wires up
the memory store, agents, tool registry and supervisor.  It defines a
Webhook endpoint for Telegram and generic endpoints for testing.

Professional-grade production hardening:
  - Structured JSON logging (machine-readable, loglevel-aware)
  - Rate limiting per IP via slowapi (100 req/min, 10 req/s burst)
  - Prometheus /metrics endpoint
  - Sentry error tracking (opt-in via SENTRY_DSN env var)
  - APScheduler cron jobs for daily report automation
  - Backup retention enforcement on every backup run
  - Debug mode (BUYEROS_DEBUG=1): verbose request logging, request ID
    propagation through the full call chain, structured error responses
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from sentry_sdk import init as sentry_init, capture_exception

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
from ..orchestration import OrchestrationStore, TraceConnectionManager, create_orchestration_router
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
    ReceiptScanRequest,
    ReconCompareRequest,
    RefundCardVerifyRequest,
    BankImportCsvRequest,
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
from ..services.xau_integration import XAUIntegration
from ..services.cloth_integration import CLOTHIntegration
from ..services.receipt_vision_service import ReceiptVisionService
from ..services.recon_store import ReconStore
from ..services.bank_import_service import BankImportService
from ..services.telegram_commands import parse_telegram_command
from ..services.admin_dashboard import render_admin_page, render_kv_card, render_table_card
from ..services.expense_service import ExpenseService, VALID_CATEGORIES, VALID_STATUSES
from ..workflows.buyeros_graph import BuyerOSGraphWorkflow

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Request-scoped debug context
# ─────────────────────────────────────────────────────────────────────────────
# Holds per-request metadata (request_id, trace_id, span_id, client_ip)
# accessible from anywhere in the call chain without passing it manually.
# Thread-safe via contextvars.

_request_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("buyeros_request_ctx", default=None)


def get_request_ctx() -> Dict[str, Any]:
    """Return current request context or empty dict."""
    return _request_ctx.get() or {}


def set_request_ctx(**kwargs: Any) -> None:
    ctx = _request_ctx.get() or {}
    ctx.update(kwargs)
    _request_ctx.set(ctx)


def clear_request_ctx() -> None:
    _request_ctx.set(None)


def get_trace_ctx() -> Dict[str, Any]:
    """Return current trace context for logging and observability.

    All agents and tool calls should call this to get the current
    request_id / trace_id so logs can be correlated end-to-end.
    """
    ctx = get_request_ctx()
    return {
        "request_id": ctx.get("request_id"),
        "trace_id": ctx.get("trace_id"),
        "client_ip": ctx.get("client_ip"),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Debug mode flag
# ─────────────────────────────────────────────────────────────────────────────

def _is_debug() -> bool:
    val = os.getenv("BUYEROS_DEBUG", "").lower()
    return val in ("1", "true", "yes")


def _is_test_env() -> bool:
    return os.getenv("BUYEROS_ENV") == "test"


# ─────────────────────────────────────────────────────────────────────────────
# Structured JSON logger  (replaces bare logger.error / logger.warning calls)
# ─────────────────────────────────────────────────────────────────────────────

class StructuredLogger:
    """Wraps stdlib logging with machine-readable JSON output.

    BUYEROS_ENV=production → JSON to stderr (machine-parseable)
    BUYEROS_DEBUG=1       → verbose text to stderr (human-readable)
    otherwise              → text to stdlib logger
    """

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)
        self._prod = os.getenv("BUYEROS_ENV", "production") == "production"

    def _enrich(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = get_request_ctx()
        base = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "service": "buyeros",
            "version": "8",
        }
        if ctx.get("request_id"):
            base["request_id"] = ctx["request_id"]
        if ctx.get("trace_id"):
            base["trace_id"] = ctx["trace_id"]
        if ctx.get("client_ip"):
            base["client_ip"] = ctx["client_ip"]
        base.update(kwargs)
        return base

    def _json(self, level: str, **kwargs: Any) -> None:
        record = self._enrich(level=level, **kwargs)
        print(json.dumps(record, default=str), file=sys.stderr)

    def _text(self, level: str, event: str, **kwargs: Any) -> None:
        parts = [f"[{level}] {event}"]
        for k, v in kwargs.items():
            if k not in ("exc_info",):
                parts.append(f"{k}={v!r}")
        self._log.log(
            getattr(logging, level, logging.INFO),
            " | ".join(parts),
            exc_info=kwargs.get("exc_info"),
        )

    def debug(self, event: str, **kwargs: Any) -> None:
        if self._prod and not _is_debug():
            self._json("DEBUG", event=event, **kwargs)
        else:
            self._text("DEBUG", event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        if self._prod and not _is_debug():
            self._json("INFO", event=event, **kwargs)
        else:
            self._text("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        if self._prod and not _is_debug():
            self._json("WARNING", event=event, **kwargs)
        else:
            self._text("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        if self._prod and not _is_debug():
            self._json("ERROR", event=event, **kwargs)
        else:
            self._text("ERROR", event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        if self._prod and not _is_debug():
            self._json("CRITICAL", event=event, **kwargs)
        else:
            self._text("CRITICAL", event, **kwargs)


_log = StructuredLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Prometheus metrics  (professional observability)
# ─────────────────────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "buyeros_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
http_request_duration_seconds = Histogram(
    "buyeros_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
active_sessions = Gauge("buyeros_active_sessions", "Number of active sessions")
memory_entries_total = Counter("buyeros_memory_entries_total", "Total memory entries written", ["namespace"])
agent_runs_total = Counter("buyeros_agent_runs_total", "Total agent runs", ["agent", "status"])
automation_runs_total = Counter("buyeros_automation_runs_total", "Total automation runs", ["workflow"])


def _patch_logger() -> None:
    """Replace module-level bare logger.* calls with structured logging."""
    global logger
    logger = _log  # type: ignore[assignment,misc]


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiter  (simple in-memory sliding-window, no third-party dependency)
# Per-IP: 100 req/min, 10 req/s burst.
# Production should use Redis-based limiter (see /metrics endpoint for observability).
# ─────────────────────────────────────────────────────────────────────────────

_window_lock = threading.Lock()
_request_windows: dict[str, list[float]] = defaultdict(list)

def _clean_window(ip: str, window_seconds: float, now: float) -> None:
    cutoff = now - window_seconds
    _request_windows[ip] = [t for t in _request_windows[ip] if t > cutoff]

def _ip_from_request(request: Request) -> str:
    """Best-effort client IP extraction (X-Forwarded-For aware)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str, rpm: int, rps: int) -> tuple[bool, str]:
    """Return (allowed, retry_after_str). thread-safe sliding window."""
    now = time.time()
    with _window_lock:
        _clean_window(ip, 60.0, now)
        _clean_window(ip, 1.0, now)
        total = len(_request_windows[ip])
        if total >= rpm:
            oldest = _request_windows[ip][0]
            retry = int(oldest + 60.0 - now) + 1
            return False, str(max(1, retry))
        if len([t for t in _request_windows[ip] if t > now - 1.0]) >= rps:
            oldest = [t for t in _request_windows[ip] if t > now - 1.0][0]
            retry = int(oldest + 1.0 - now) + 1
            return False, str(max(1, retry))
        _request_windows[ip].append(now)
        return True, "0"


def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""

    # ── Sentry ──────────────────────────────────────────────────────────────
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_init(
            dsn=sentry_dsn,
            environment=os.getenv("BUYEROS_ENV", "production"),
            release=os.getenv("BUYEROS_VERSION", "8.0.0"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        )
        _log.info("sentry_init", dsn_masked=f"***{sentry_dsn[-8:]}")

    # ── Rate limiter ────────────────────────────────────────────────────────
    app = FastAPI(
        title="BuyerOS API",
        docs_url="/docs" if os.getenv("BUYEROS_ENV") != "production" else None,
        redoc_url="/redoc" if os.getenv("BUYEROS_ENV") != "production" else None,
    )
    # ── Rate limiter ────────────────────────────────────────────────────────
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if _is_test_env():
            return await call_next(request)
        ip = _ip_from_request(request)
        allowed, retry_after = _check_rate_limit(ip, rpm=100, rps=10)
        if not allowed:
            _log.warning("rate_limit_exceeded", ip=ip, path=request.url.path)
            return Response(
                content=f'{{"detail":"Rate limit exceeded","retry_after":"{retry_after}"}}',
                status_code=429,
                headers={"Retry-After": retry_after, "X-RateLimit-Limit": "100/minute"},
                media_type="application/json",
            )
        return await call_next(request)

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

    # ── Middleware: request logging + metrics ───────────────────────────────
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        span_id = str(uuid.uuid4())[:8]
        client_ip = _ip_from_request(request)
        start = time.perf_counter()

        # Populate both old request-ctx and new trace context
        set_request_ctx(request_id=request_id, trace_id=trace_id, client_ip=client_ip)
        try:
            from ..trace import set_trace, clear_trace
            set_trace(request_id=request_id, trace_id=trace_id, span_id=span_id, client_ip=client_ip)
        except ImportError:
            pass
        response = await call_next(request)
        duration = time.perf_counter() - start
        endpoint = request.url.path
        status = str(response.status_code)

        # Prometheus metrics
        http_requests_total.labels(method=request.method, endpoint=endpoint, status_code=status).inc()
        http_request_duration_seconds.labels(method=request.method, endpoint=endpoint).observe(duration)

        # Response headers
        response.headers["x-request-id"] = request_id
        response.headers["x-trace-id"] = trace_id
        response.headers["x-span-id"] = span_id

        # Structured log
        log_data: Dict[str, Any] = {
            "method": request.method,
            "path": endpoint,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "request_id": request_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", ""),
            "content_length": request.headers.get("content-length", ""),
        }
        if _is_debug():
            log_data["debug"] = True
            log_data["query_params"] = dict(request.query_params)
            log_data["auth_header_present"] = bool(request.headers.get("authorization"))
            log_data["referer"] = request.headers.get("referer", "")
        _log.info("http_request", **log_data)

        # Clean up trace context
        try:
            from ..trace import clear_trace
            clear_trace()
        except ImportError:
            pass
        return response
    # Setup memory store (Supabase if env vars present, otherwise memory)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    memory_store = MemoryStore(supabase_url=supabase_url, supabase_key=supabase_key)

    # Setup AI router
    ai_router = AIModelRouter()
    context_hub = ContextHub(memory_store)
    session_store = RedisSessionStore(os.getenv("REDIS_URL"))
    orchestration_store = OrchestrationStore(os.getenv("REDIS_URL"))
    orchestration_manager = TraceConnectionManager()
    audit_logger = AuditLogger(memory_store)
    reporting_service = ReportingService(memory_store)
    promo_service = PromoService(memory_store)
    task_board_service = TaskBoardService(memory_store)
    project_registry = ProjectRegistryService(memory_store)
    timeline_service = MemoryTimelineService(memory_store)
    ops_status_service = OpsStatusService()
    receipt_vision = ReceiptVisionService()
    recon_store = ReconStore()
    bank_import = BankImportService()

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

    # Initialize XAU and CLOTH integrations if configured
    xau_integration = None
    cloth_integration = None
    xau_base_url = os.environ.get("XAU_BASE_URL", "")
    cloth_base_url = os.environ.get("CLOTH_BASE_URL", "")

    if xau_base_url:
        from ..services.xau_integration import XAUConfig
        xau_integration = XAUIntegration(XAUConfig(base_url=xau_base_url))
        logger.info("XAU integration initialized", extra={"xau_base_url": xau_base_url})

    if cloth_base_url:
        from ..services.cloth_integration import CLOTHConfig
        cloth_integration = CLOTHIntegration(CLOTHConfig(base_url=cloth_base_url))
        logger.info("CLOTH integration initialized", extra={"cloth_base_url": cloth_base_url})

    dispatcher_service = TaskDispatcherService(
        memory_store=memory_store,
        task_board=task_board_service,
        projects=project_registry,
        providers=provider_registry,
        context_hub=context_hub,
        ops_agent=ops_agent,
        finance_agent=finance_agent,
        xau_integration=xau_integration,
        cloth_integration=cloth_integration,
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
    app.state.orchestration_store = orchestration_store
    app.state.orchestration_manager = orchestration_manager
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
    app.state.receipt_vision = receipt_vision
    app.state.recon_store = recon_store
    app.state.bank_import = bank_import
    app.state.orders_service = orders_service
    app.state.buyers_service = buyers_service

    expense_service = ExpenseService()
    app.state.expense_service = expense_service

    @app.on_event("startup")
    async def _startup_orchestration() -> None:
        await orchestration_store.connect()

    @app.on_event("shutdown")
    async def _shutdown_orchestration() -> None:
        await orchestration_store.close()

    app.include_router(create_orchestration_router(orchestration_store, orchestration_manager))

    @app.post("/telegram/webhook")
    async def telegram_webhook(request: Request) -> JSONResponse:
        """Handle incoming Telegram updates via webhook."""
        expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if expected_secret and request.headers.get("x-telegram-bot-api-secret-token") != expected_secret:
            raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
        try:
            update: Dict[str, Any] = await request.json()
        except Exception as exc:
            _log.error("telegram_parse_failed", error=str(exc), exc_info=True)
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

        # Prefer explicit recon commands over intent routing.
        cmd = parse_telegram_command(text)
        if cmd:
            name, args = cmd
            try:
                if name == "scan":
                    if not args.get("image_url") or not args.get("buyer_id"):
                        response_text = "用法：/scan <image_url> buyer=<id> team=<id?> decl=<id?> date=<YYYY-MM-DD?>"
                    else:
                        result = await recon_receipt_scan(ReceiptScanRequest(**args))
                        if result.get("ok"):
                            response_text = (
                                f"已掃描\nscan_id={result.get('scan_id')}\nitems={result.get('items_count')}\n"
                                f"total_hkd={result.get('total_amount_hkd')}\nmodel={result.get('model')}"
                            )
                        else:
                            response_text = f"掃描失敗：{result.get('error') or 'unknown_error'}"

                elif name == "compare":
                    if not args.get("declaration_id") or not args.get("scan_id") or not args.get("buyer_id"):
                        response_text = "用法：/compare decl=<id> scan=<id> buyer=<id> team=<id?> threshold=<0.72?> date=<YYYY-MM-DD?>"
                    else:
                        # Parse threshold if present
                        if args.get("threshold") is not None:
                            try:
                                args["threshold"] = float(args["threshold"])  # type: ignore
                            except Exception:
                                args["threshold"] = 0.72
                        result = await recon_compare(ReconCompareRequest(**args))
                        response_text = (
                            f"對照完成\ncmp_id={result.get('comparison_id')}\n"
                            f"risk={result.get('risk_level')}\nflags={','.join(result.get('risk_flags') or [])}\n"
                            f"diff_hkd={result.get('diff_hkd')}\nmatched={((result.get('stats') or {}).get('matched_count'))}"
                        )

                elif name == "refundcard":
                    if not args.get("return_id") or not args.get("refund_card_last4"):
                        response_text = "用法：/refundcard return=<id> last4=<1234> buyer=<id?> team=<id?>"
                    else:
                        result = await refund_card_verify(RefundCardVerifyRequest(**args))
                        response_text = (
                            f"卡號核對\nver_id={result.get('verification_id')}\nmatch={result.get('card_match')}\n"
                            f"risk={result.get('risk_level')}\nflags={','.join(result.get('risk_flags') or [])}"
                        )

                else:
                    response_text = "未知指令。"
            except Exception as exc:
                response_text = f"指令執行錯誤：{exc}"
        else:
            response_text = workflow.handle_message(user_id=user_id, message=text, channel="telegram", session_id=user_id)
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(send_url, json={"chat_id": chat_id, "text": response_text})
            except Exception as exc:
                _log.error("telegram_send_failed", error=str(exc), exc_info=True, chat_id=chat_id)
        return JSONResponse(content={"ok": True})

    # ── Stripe webhook ────────────────────────────────────────────────────────
    @app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request) -> JSONResponse:
        """Handle Stripe webhook events for real-time payment/refund events.

        Configure in Stripe dashboard:
          endpoint = https://<your-domain>/webhooks/stripe
          events  = payment_intent.succeeded, charge.refunded,
                    refund.failed, customer.subscription.updated
        Requires STRIPE_WEBHOOK_SECRET env var for signature verification.
        """
        stripe_secret = os.getenv("STRIPE_SECRET_KEY", "")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        # Verify signature (skip in dev if no secret configured)
        if webhook_secret and stripe_secret:
            try:
                from stripe import Webhook, SignatureVerificationError
                try:
                    Webhook.construct_event(payload, sig_header, webhook_secret)
                except SignatureVerificationError as exc:
                    _log.warning("stripe_webhook_signature_invalid", error=str(exc))
                    raise HTTPException(status_code=400, detail="Invalid Stripe signature")
            except ImportError:
                _log.warning("stripe_lib_not_installed_skip_signature_check")

        try:
            import json as _json
            event = _json.loads(payload)
        except Exception as exc:
            _log.error("stripe_webhook_parse_failed", error=str(exc))
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        if event_type == "charge.refunded":
            tx_id = data.get("payment_intent") or data.get("id", "")
            amount = (data.get("amount", 0) or 0) / 100  # stripe uses cents
            currency = data.get("currency", "hkd").upper()
            memory_store.save_memory(
                ["buyeros", "refunds"],
                f"stripe-{tx_id}",
                {"provider": "stripe", "tx_id": tx_id, "amount": amount, "currency": currency, "event": event_type, "raw": data},
                created_by="stripe_webhook",
            )
            _log.info("stripe_refund_recorded", tx_id=tx_id, amount=amount, currency=currency)

        elif event_type == "payment_intent.succeeded":
            tx_id = data.get("id", "")
            amount = (data.get("amount", 0) or 0) / 100
            memory_store.save_memory(
                ["buyeros", "orders"],
                f"stripe-{tx_id}",
                {"provider": "stripe", "tx_id": tx_id, "amount": amount, "status": "paid", "raw": data},
                created_by="stripe_webhook",
            )
            _log.info("stripe_payment_recorded", tx_id=tx_id, amount=amount)

        elif event_type == "refund.failed":
            tx_id = data.get("payment_intent") or data.get("id", "")
            memory_store.save_memory(
                ["buyeros", "refunds"],
                f"stripe-refund-failed-{tx_id}",
                {"provider": "stripe", "tx_id": tx_id, "status": "failed", "raw": data},
                created_by="stripe_webhook",
            )
            _log.warning("stripe_refund_failed", tx_id=tx_id)

        else:
            _log.info("stripe_webhook_unhandled", event_type=event_type)

        return JSONResponse(content={"received": True})

    @app.post("/context/write", dependencies=[Depends(require_api_key)], tags=["Context"])
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

    @app.post("/context/summarize", dependencies=[Depends(require_api_key)], tags=["Context"])
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

    @app.post("/recon/receipt/scan", dependencies=[Depends(require_api_key)], tags=["Recon"])
    async def recon_receipt_scan(payload: ReceiptScanRequest) -> Dict[str, Any]:
        """Extract receipt items via OpenRouter Vision and persist to Supabase."""
        if not receipt_vision.configured():
            raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured")
        if not recon_store.configured():
            raise HTTPException(status_code=400, detail="SUPABASE_URL/SUPABASE_KEY not configured")

        vision = receipt_vision.extract_receipt(
            image_url=payload.image_url,
            scan_id=payload.scan_id,
            receipt_date=payload.date,
        )
        if not vision.ok:
            audit_logger.log(
                action="recon.receipt_scan.failed",
                actor="api",
                details={"buyer_id": payload.buyer_id, "error": vision.error, "scan_id": vision.scan_id},
            )
            return {"ok": False, "scan_id": vision.scan_id, "error": vision.error, "provider": vision.provider, "model": vision.model}

        scan_date = payload.date or (vision.date or datetime.now(timezone.utc).date().isoformat())
        # Insert scan row
        recon_store.insert_receipt_scan(
            scan_id=vision.scan_id,
            buyer_id=payload.buyer_id,
            team_id=payload.team_id,
            declaration_id=payload.declaration_id,
            scan_date=scan_date,
            image_url=payload.image_url,
            raw_text=None,
            total_amount_hkd=vision.total_amount_hkd,
            ai_provider=vision.provider,
            ai_confidence=None,
            ai_model=vision.model,
            raw=vision.raw,
        )
        # Insert items
        items_payload = [
            {
                "item_name": it.item_name,
                "quantity": it.quantity,
                "unit_price_hkd": it.unit_price_hkd,
                "subtotal_hkd": it.subtotal_hkd,
                "ai_confidence": it.ai_confidence,
            }
            for it in vision.items
        ]
        recon_store.insert_receipt_items(scan_id=vision.scan_id, items=items_payload)

        audit_logger.log(
            action="recon.receipt_scan.completed",
            actor="api",
            details={
                "buyer_id": payload.buyer_id,
                "team_id": payload.team_id,
                "declaration_id": payload.declaration_id,
                "scan_id": vision.scan_id,
                "items": len(items_payload),
                "total_amount_hkd": vision.total_amount_hkd,
            },
        )

        return {
            "ok": True,
            "scan_id": vision.scan_id,
            "date": scan_date,
            "merchant": vision.merchant,
            "currency": vision.currency,
            "total_amount_hkd": vision.total_amount_hkd,
            "items_count": len(items_payload),
            "model": vision.model,
        }

    @app.post("/recon/compare", dependencies=[Depends(require_api_key)], tags=["Recon"])
    async def recon_compare(payload: ReconCompareRequest) -> Dict[str, Any]:
        """Compare a declaration and a receipt scan into item_comparisons (MVP fuzzy match)."""
        if not recon_store.configured():
            raise HTTPException(status_code=400, detail="SUPABASE_URL/SUPABASE_KEY not configured")

        declared_items = recon_store.fetch_declaration_items(declaration_id=payload.declaration_id)
        scanned_items = recon_store.fetch_receipt_items(scan_id=payload.scan_id)
        if not declared_items:
            raise HTTPException(status_code=404, detail="declaration_items not found")
        if not scanned_items:
            raise HTTPException(status_code=404, detail="receipt_items not found")

        from ..services.recon_matching import match_items

        match = match_items(
            declared=declared_items,
            scanned=scanned_items,
            threshold=payload.threshold,
        )

        declared_total = sum(int(it.get("subtotal_hkd") or 0) for it in declared_items)
        scanned_total = sum(int(it.get("subtotal_hkd") or 0) for it in scanned_items)
        diff = scanned_total - declared_total

        has_missing = match["stats"]["missing_declared_count"] > 0
        has_undeclared = match["stats"]["undeclared_scanned_count"] > 0
        has_mismatch = match["stats"]["mismatched_count"] > 0
        all_matched = (not has_missing) and (not has_undeclared) and (not has_mismatch)

        risk_flags = []
        if has_missing:
            risk_flags.append("missing_declared_items")
        if has_undeclared:
            risk_flags.append("undeclared_scanned_items")
        if has_mismatch:
            risk_flags.append("price_or_quantity_mismatch")
        if abs(diff) >= 5000:  # HKD 50
            risk_flags.append("total_diff_over_hkd_50")

        risk_level = "low"
        if has_undeclared or has_missing:
            risk_level = "medium"
        if has_undeclared and abs(diff) >= 20000:
            risk_level = "high"

        comparison_id = f"cmp-{uuid.uuid4().hex[:12]}"
        compare_date = payload.date or datetime.now(timezone.utc).date().isoformat()

        comparison_payload = {
            "comparison_id": comparison_id,
            "declaration_id": payload.declaration_id,
            "scan_id": payload.scan_id,
            "buyer_id": payload.buyer_id,
            "team_id": payload.team_id,
            "date": compare_date,

            "has_missing_items": has_missing,
            "has_undeclared_items": has_undeclared,
            "has_extra_items": False,
            "has_price_mismatch": has_mismatch,
            "has_quantity_mismatch": has_mismatch,
            "has_unmatched_declared": has_missing,
            "all_matched": all_matched,

            "declared_total_hkd": declared_total,
            "scanned_total_hkd": scanned_total,
            "price_difference_hkd": diff,

            "missing_items": match["missing_declared"],
            "undeclared_items": match["undeclared_scanned"],
            "mismatched_items": match["mismatched"],

            "risk_level": risk_level,
            "risk_flags": risk_flags,

            "status": "pending",
        }

        recon_store.insert_item_comparison(payload=comparison_payload)

        audit_logger.log(
            action="recon.compare.completed",
            actor="api",
            details={
                "comparison_id": comparison_id,
                "buyer_id": payload.buyer_id,
                "team_id": payload.team_id,
                "declaration_id": payload.declaration_id,
                "scan_id": payload.scan_id,
                "risk_level": risk_level,
                "flags": risk_flags,
            },
        )

        return {
            "ok": True,
            "comparison_id": comparison_id,
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "declared_total_hkd": declared_total,
            "scanned_total_hkd": scanned_total,
            "diff_hkd": diff,
            "stats": match["stats"],
        }

    @app.post("/recon/refund-card/verify", dependencies=[Depends(require_api_key)], tags=["Recon"])
    async def refund_card_verify(payload: RefundCardVerifyRequest) -> Dict[str, Any]:
        """Verify refund card last4 against buyer registered cards and persist verification."""
        if not recon_store.configured():
            raise HTTPException(status_code=400, detail="SUPABASE_URL/SUPABASE_KEY not configured")

        ret = recon_store.fetch_return(return_id=payload.return_id)
        if not ret:
            raise HTTPException(status_code=404, detail="return not found")

        buyer_id = payload.buyer_id or str(ret.get("buyer_id") or "")
        if not buyer_id:
            raise HTTPException(status_code=400, detail="buyer_id missing")

        team_id = payload.team_id or (ret.get("team_id") if isinstance(ret.get("team_id"), str) else None)
        refund_last4 = str(payload.refund_card_last4).strip()

        cards = recon_store.fetch_payment_cards_for_buyer(buyer_id=buyer_id)
        active_cards = [c for c in cards if c.get("is_active") is not False]
        known_last4 = {str(c.get("card_last4") or "").strip() for c in active_cards if c.get("card_last4")}

        card_match = refund_last4 in known_last4 if refund_last4 else False
        any_verified = any(bool(c.get("is_verified")) for c in active_cards)

        risk_flags = []
        if not cards:
            risk_flags.append("no_cards_on_file")
        if not card_match:
            risk_flags.append("refund_card_last4_mismatch")
        if cards and not any_verified:
            risk_flags.append("cards_unverified")

        risk_level = "low"
        if not card_match:
            risk_level = "medium" if cards else "high"

        verification_id = f"ver-{uuid.uuid4().hex[:12]}"
        ver_payload = {
            "verification_id": verification_id,
            "buyer_id": buyer_id,
            "team_id": team_id,
            "return_id": payload.return_id,
            "refund_card_last4": refund_last4,
            "refund_amount_hkd": ret.get("refund_amount_hkd"),
            "card_match": card_match,
            "card_verified": any_verified,
            "verification_status": "completed",
            "risk_level": risk_level,
            "risk_flags": risk_flags,
        }
        recon_store.insert_refund_card_verification(payload=ver_payload)

        audit_logger.log(
            action="recon.refund_card_verify.completed",
            actor="api",
            details={
                "verification_id": verification_id,
                "return_id": payload.return_id,
                "buyer_id": buyer_id,
                "team_id": team_id,
                "card_match": card_match,
                "risk_level": risk_level,
                "risk_flags": risk_flags,
            },
        )

        return {
            "ok": True,
            "verification_id": verification_id,
            "return_id": payload.return_id,
            "buyer_id": buyer_id,
            "team_id": team_id,
            "card_match": card_match,
            "known_last4": sorted([x for x in known_last4 if x]),
            "risk_level": risk_level,
            "risk_flags": risk_flags,
        }

    @app.post("/recon/bank/import-csv", dependencies=[Depends(require_api_key)], tags=["Recon"])
    async def recon_bank_import_csv(
        request: Request,
        bank_code: str = Form(...),
        account_id: str = Form(...),
        currency: str = Form("HKD"),
        team_id: Optional[str] = Form(None),
        buyer_id: Optional[str] = Form(None),
        statement_id: Optional[str] = Form(None),
        reference: str = Form("bank-import-csv"),
        source: str = Form("api"),
        file: UploadFile = File(...),
    ) -> Dict[str, Any]:
        """Import a bank statement CSV (multi-bank via bank_code)."""
        if not bank_import.configured():
            raise HTTPException(status_code=400, detail="SUPABASE_URL/SUPABASE_KEY not configured")

        raw = await file.read()
        try:
            content = raw.decode("utf-8")
        except Exception:
            content = raw.decode("utf-8", errors="ignore")

        result = bank_import.import_csv(
            bank_code=bank_code,
            account_id=account_id,
            currency=currency,
            content=content,
            team_id=team_id,
            buyer_id=buyer_id,
            statement_id=statement_id,
            source=source,
            reference=reference,
        )

        audit_logger.log(
            action="recon.bank_import_csv",
            actor="api",
            details={
                "bank_code": bank_code,
                "account_id": account_id,
                "currency": currency,
                "statement_id": result.get("statement_id"),
                "ok": result.get("ok"),
                "transactions": result.get("transactions"),
            },
        )

        return result

    @app.post("/recon/bank/import-manual", dependencies=[Depends(require_api_key)], tags=["Recon"])
    async def recon_bank_import_manual(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Import bank transactions from manual JSON payload.

        Expected payload:
          {
            "bank_code": "za_hk",
            "account_id": "za-main",
            "currency": "HKD|GBP|USDT",
            "team_id": "..."?,
            "buyer_id": "..."?,
            "statement_id": "..."?,
            "reference": "..."?,
            "source": "api"?,
            "raw_text": "..."?,
            "transactions": [
              {"date": "YYYY-MM-DD", "description": "...", "amount_major": 12.34, "balance_major": 56.78?},
              ...
            ]
          }
        """
        if not bank_import.configured():
            raise HTTPException(status_code=400, detail="SUPABASE_URL/SUPABASE_KEY not configured")

        from ..services.bank_manual_import import major_to_minor

        bank_code = str(payload.get("bank_code") or "").strip()
        account_id = str(payload.get("account_id") or "").strip()
        currency = str(payload.get("currency") or "HKD").strip()
        if not bank_code or not account_id:
            raise HTTPException(status_code=400, detail="bank_code/account_id required")

        txs_in = payload.get("transactions") or []
        if not isinstance(txs_in, list) or not txs_in:
            raise HTTPException(status_code=400, detail="transactions required")

        txs = []
        for t in txs_in:
            if not isinstance(t, dict):
                continue
            date = t.get("date")
            desc = t.get("description")
            amt_major = t.get("amount_major")
            bal_major = t.get("balance_major")
            if date is None or amt_major is None:
                continue
            txs.append(
                {
                    "date": str(date),
                    "description": str(desc or "(no description)"),
                    "amount": major_to_minor(float(amt_major), currency=currency),
                    "currency": currency.upper(),
                    "balance": major_to_minor(float(bal_major), currency=currency) if bal_major is not None else None,
                    "reference": t.get("reference"),
                }
            )

        result = bank_import.import_manual(
            bank_code=bank_code,
            account_id=account_id,
            currency=currency,
            transactions=txs,
            team_id=payload.get("team_id"),
            buyer_id=payload.get("buyer_id"),
            statement_id=payload.get("statement_id"),
            source=str(payload.get("source") or "api"),
            reference=str(payload.get("reference") or "bank-import-manual"),
            raw_text=payload.get("raw_text"),
        )

        audit_logger.log(
            action="recon.bank_import_manual",
            actor="api",
            details={
                "bank_code": bank_code,
                "account_id": account_id,
                "currency": currency,
                "statement_id": result.get("statement_id"),
                "ok": result.get("ok"),
                "transactions": result.get("transactions"),
            },
        )

        return result

    @app.get("/admin", tags=["Admin"])
    async def admin_dashboard(request: Request, token: Optional[str] = None) -> Response:
        """Minimal admin dashboard (server-rendered).

        Auth options:
        - Standard API key header (same as other endpoints)
        - Query token (?token=...) when ADMIN_DASHBOARD_TOKEN is configured
        """
        expected_query_token = os.getenv("ADMIN_DASHBOARD_TOKEN")

        if expected_query_token:
            if token != expected_query_token:
                raise HTTPException(status_code=401, detail="Invalid or missing admin token")
        else:
            await require_api_key(request)

        def _admin_url(path: str) -> str:
            return f"{path}?token={token}" if expected_query_token else path

        blocks = []

        blocks.append(
            "<div class=\"grid\">"
            + render_kv_card(
                "Services",
                {
                    "supabase": "ok" if recon_store.configured() else "missing SUPABASE_URL/SUPABASE_KEY",
                    "openrouter": "ok" if receipt_vision.configured() else "missing OPENROUTER_API_KEY",
                    "bank_import": "ok" if bank_import.configured() else "missing SUPABASE_URL/SUPABASE_KEY",
                },
            )
            + render_kv_card(
                "Bank parsers",
                {
                    "registered": ", ".join(bank_import.parsers.list_codes()),
                    "note": "use /recon/bank/import-csv with bank_code",
                },
            )
            + "</div>"
        )

        if recon_store.configured():
            try:
                supa = recon_store.supabase
                statements = (
                    supa.table("bank_statements")
                    .select("statement_id,bank_code,account_id,currency,period_start,period_end,imported_at,status")
                    .order("imported_at", desc=True)
                    .limit(20)
                    .execute()
                ).data or []

                rows = []
                for s in statements:
                    sid = s.get("statement_id")
                    sid_link = f"<a href=\"{_admin_url('/admin/statements/' + str(sid))}\">{sid}</a>" if sid else ""
                    rows.append(
                        [
                            sid_link,
                            s.get("bank_code"),
                            s.get("account_id"),
                            s.get("currency"),
                            f"{s.get('period_start')} → {s.get('period_end')}",
                            s.get("status"),
                        ]
                    )
                blocks.append(
                    render_table_card(
                        "Recent bank statements",
                        headers=["statement_id", "bank", "account", "ccy", "period", "status"],
                        rows=rows,
                    )
                )

                comps = (
                    supa.table("item_comparisons")
                    .select("comparison_id,date,buyer_id,team_id,declaration_id,scan_id,risk_level,status")
                    .order("date", desc=True)
                    .limit(20)
                    .execute()
                ).data or []

                rows2 = []
                for c in comps:
                    cid = c.get("comparison_id")
                    cid_link = f"<a href=\"{_admin_url('/admin/comparisons/' + str(cid))}\">{cid}</a>" if cid else ""
                    rows2.append(
                        [
                            cid_link,
                            c.get("date"),
                            c.get("risk_level"),
                            c.get("status"),
                            c.get("declaration_id"),
                            c.get("scan_id"),
                        ]
                    )
                blocks.append(
                    render_table_card(
                        "Recent recon comparisons",
                        headers=["comparison_id", "date", "risk", "status", "declaration_id", "scan_id"],
                        rows=rows2,
                    )
                )
            except Exception as exc:
                blocks.append(render_kv_card("Admin error", {"error": str(exc)}))

        html = render_admin_page(title="BuyerOS Admin", blocks=blocks)
        return Response(content=html, media_type="text/html")

    @app.get("/admin/statements/{statement_id}", tags=["Admin"])
    async def admin_statement_detail(statement_id: str, request: Request, token: Optional[str] = None) -> Response:
        expected_query_token = os.getenv("ADMIN_DASHBOARD_TOKEN")
        if expected_query_token:
            if token != expected_query_token:
                raise HTTPException(status_code=401, detail="Invalid or missing admin token")
        else:
            await require_api_key(request)

        if not recon_store.configured():
            return Response(content=render_admin_page(title="BuyerOS Admin", blocks=[render_kv_card("Error", {"error": "supabase_not_configured"})]), media_type="text/html")

        supa = recon_store.supabase
        stmt = (
            supa.table("bank_statements")
            .select("statement_id,bank_code,account_id,currency,period_start,period_end,imported_at,status,file_hash")
            .eq("statement_id", statement_id)
            .limit(1)
            .execute()
        ).data or []

        txs = (
            supa.table("bank_transactions")
            .select("transaction_id,date,description,amount,currency,balance,is_reconciled")
            .eq("statement_id", statement_id)
            .order("date", desc=False)
            .limit(200)
            .execute()
        ).data or []

        blocks = []
        blocks.append("<div style=\"margin-bottom:10px\"><a href=\"/admin?token=" + _escape(token) + "\">← back</a></div>" if expected_query_token else "<div style=\"margin-bottom:10px\"><a href=\"/admin\">← back</a></div>")
        blocks.append(render_kv_card("Statement", stmt[0] if stmt else {"statement_id": statement_id, "found": False}))
        rows = []
        for t in txs:
            rows.append([t.get("date"), t.get("description"), t.get("amount"), t.get("currency"), t.get("balance"), t.get("is_reconciled")])
        blocks.append(render_table_card("Transactions (first 200)", headers=["date", "description", "amount", "ccy", "balance", "reconciled"], rows=rows))
        html = render_admin_page(title=f"Statement {statement_id}", blocks=blocks)
        return Response(content=html, media_type="text/html")

    @app.get("/admin/comparisons/{comparison_id}", tags=["Admin"])
    async def admin_comparison_detail(comparison_id: str, request: Request, token: Optional[str] = None) -> Response:
        expected_query_token = os.getenv("ADMIN_DASHBOARD_TOKEN")
        if expected_query_token:
            if token != expected_query_token:
                raise HTTPException(status_code=401, detail="Invalid or missing admin token")
        else:
            await require_api_key(request)

        if not recon_store.configured():
            return Response(content=render_admin_page(title="BuyerOS Admin", blocks=[render_kv_card("Error", {"error": "supabase_not_configured"})]), media_type="text/html")

        supa = recon_store.supabase
        comp = (
            supa.table("item_comparisons")
            .select("comparison_id,date,buyer_id,team_id,declaration_id,scan_id,risk_level,status,stats")
            .eq("comparison_id", comparison_id)
            .limit(1)
            .execute()
        ).data or []

        mismatches = (
            supa.table("item_mismatches")
            .select("mismatch_id,comparison_id,sku,declared_qty,scanned_qty,declared_price,scanned_price,reason")
            .eq("comparison_id", comparison_id)
            .limit(200)
            .execute()
        ).data or []

        blocks = []
        blocks.append("<div style=\"margin-bottom:10px\"><a href=\"/admin?token=" + _escape(token) + "\">← back</a></div>" if expected_query_token else "<div style=\"margin-bottom:10px\"><a href=\"/admin\">← back</a></div>")
        blocks.append(render_kv_card("Comparison", comp[0] if comp else {"comparison_id": comparison_id, "found": False}))

        rows = []
        for m in mismatches:
            rows.append([m.get("sku"), m.get("declared_qty"), m.get("scanned_qty"), m.get("declared_price"), m.get("scanned_price"), m.get("reason")])
        blocks.append(render_table_card("Mismatches (first 200)", headers=["sku", "declared_qty", "scanned_qty", "declared_price", "scanned_price", "reason"], rows=rows))

        html = render_admin_page(title=f"Comparison {comparison_id}", blocks=blocks)
        return Response(content=html, media_type="text/html")

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

    @app.post("/agents/run", dependencies=[Depends(require_api_key)], tags=["Agents"])
    async def agents_run(payload: AgentRunRequest) -> Dict[str, Any]:
        """Run a task through the BuyerOS graph/provider layer."""
        try:
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
            agent_runs_total.labels(agent=payload.provider or "auto", status="success").inc()
            return {"ok": True, "reply": reply}
        except Exception as exc:
            agent_runs_total.labels(agent=payload.provider or "auto", status="error").inc()
            _log.error("agents_run_failed", error=str(exc), exc_info=True, user_id=payload.user_id)
            if sentry_dsn:
                capture_exception(exc)
            raise

    @app.get("/ping")
    async def ping() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus /metrics endpoint. No auth required (internal use only)."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def _all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        ctx = get_request_ctx()
        req_id = ctx.get("request_id", "unknown")
        trace_id = ctx.get("trace_id", "unknown")
        exc_type = type(exc).__name__
        exc_msg = str(exc)
        if sentry_dsn:
            capture_exception(exc)
        _log.error(
            "unhandled_exception",
            exc_type=exc_type,
            exc_message=exc_msg,
            path=str(request.url.path),
            method=request.method,
            request_id=req_id,
            trace_id=trace_id,
            exc_info=True,
        )
        status = 500
        detail = exc_msg
        if isinstance(exc, HTTPException):
            status = exc.status_code
            detail = exc.detail
        return JSONResponse(
            status_code=status,
            content={
                "ok": False,
                "error": exc_type,
                "message": detail,
                "request_id": req_id,
                "trace_id": trace_id,
            },
            headers={"x-request-id": req_id, "x-trace-id": trace_id},
        )

    @app.get("/debug/info")
    async def debug_info() -> JSONResponse:
        return JSONResponse({
            "ok": True,
            "debug_mode": _is_debug(),
            "version": "8",
            "env": os.getenv("BUYEROS_ENV", "unknown"),
            "rate_limit": {"rpm": 100, "rps": 10, "strategy": "sliding_window"},
            "features": {
                "sentry": bool(sentry_dsn),
                "prometheus": True,
                "scheduler": True,
                "stripe_webhook": True,
                "structured_logging": True,
                "rate_limiting": True,
                "nextauth": True,
            },
            "memory_store": memory_store.status(),
            "redis_store": session_store.status(),
            "orchestration": orchestration_store.status(),
            "providers": provider_registry.status(),
        })

    @app.get("/", tags=["Meta"])
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

    @app.get("/health/ready", tags=["Meta"])
    async def ready() -> Dict[str, Any]:
        """Readiness check for deployment probes and VPS smoke tests."""
        memory_status = memory_store.status()
        redis_status = session_store.status()
        orchestration_status = orchestration_store.status()
        providers = provider_registry.status()
        router_status = ai_router.status() if "ai_router" in dir() else {}
        return {
            "ok": bool(memory_status.get("ok")),
            "memory": memory_status,
            "redis": redis_status,
            "orchestration": orchestration_status,
            "providers": providers,
            "ai_router": router_status,
            "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            "api_key_required": bool(os.getenv("BUYEROS_API_KEY")),
        }

    # ── APScheduler cron jobs ────────────────────────────────────────────────
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        _scheduler = BackgroundScheduler()

        def _cron_daily_report() -> None:
            """Run at 07:00 UTC every day."""
            try:
                result = business_automation.create_daily_report()
                _log.info(
                    "cron_daily_report_completed",
                    workflow="daily_report",
                    status=result.get("status"),
                    report_date=result.get("data", {}).get("date"),
                )
                automation_runs_total.labels(workflow="daily_report").inc()
            except Exception as exc:
                _log.error("cron_daily_report_failed", error=str(exc), exc_info=True)
                if sentry_dsn:
                    capture_exception(exc)

        def _cron_backup_retention() -> None:
            """Prune backup archives older than RETENTION_DAYS (default 30)."""
            import glob as _glob
            import os as _os
            retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
            backup_dir = os.getenv("BUYEROS_BACKUP_DIR", "/opt/buyeros-backups")
            cutoff = time.time() - (retention_days * 86400)
            deleted = 0
            for path in _glob.glob(f"{backup_dir}/buyeros-*.tgz"):
                if _os.path.getmtime(path) < cutoff:
                    try:
                        _os.remove(path)
                        deleted += 1
                    except Exception:
                        pass
            _log.info("cron_backup_retention_completed", retention_days=retention_days, deleted=deleted)

        # Schedule daily report at 07:00 UTC (15:00 HKT)
        _scheduler.add_job(
            _cron_daily_report,
            CronTrigger(hour=7, minute=0, timezone="UTC"),
            id="daily_report",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        _scheduler.add_job(
            _cron_backup_retention,
            CronTrigger(hour=6, minute=30, timezone="UTC"),
            id="backup_retention",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        _scheduler.start()
        _log.info("scheduler_started", jobs=["daily_report", "backup_retention"])

        @app.on_event("shutdown")
        def _shutdown_scheduler() -> None:
            _scheduler.shutdown(wait=False)
            _log.info("scheduler_stopped")
    except Exception as exc:
        _log.warning("scheduler_init_skipped", reason=str(exc))

    @app.get("/providers", dependencies=[Depends(require_api_key)], tags=["Providers"])
    async def providers() -> Dict[str, Any]:
        """List configured provider adapters and model routing defaults."""
        return {"ok": True, "providers": provider_registry.status()}

    @app.get("/ai-team/status", dependencies=[Depends(require_api_key)], tags=["Providers"])
    async def ai_team_status() -> Dict[str, Any]:
        """Return AI provider readiness for the operator UI."""
        return {"ok": True, "providers": provider_registry.status()}

    @app.get("/projects", dependencies=[Depends(require_api_key)], tags=["Projects"])
    async def projects_list(limit: int = 50) -> Dict[str, Any]:
        """List registered projects (core + external)."""
        return project_registry.list_projects(limit=min(max(limit, 1), 200))

    @app.post("/projects", dependencies=[Depends(require_api_key)], tags=["Projects"])
    async def projects_upsert(payload: ProjectUpsertRequest) -> Dict[str, Any]:
        """Create or update a project entry."""
        return project_registry.upsert_project(project_id=payload.project_id, content=payload.model_dump(), created_by="api")

    @app.post("/memory/timeline", dependencies=[Depends(require_api_key)], tags=["Memory"])
    async def memory_timeline(payload: MemoryTimelineRequest) -> Dict[str, Any]:
        """Query a merged timeline across key namespaces."""
        return timeline_service.timeline(
            project_id=payload.project_id,
            session_id=payload.session_id,
            query=payload.query,
            limit=payload.limit,
        )

    @app.get("/audit/search", dependencies=[Depends(require_api_key)], tags=["Audit"])
    async def audit_search(limit: int = 20) -> Dict[str, Any]:
        """Return recent audit events."""
        items = memory_store.search_memory(namespace_prefix=("buyeros", "audit"), limit=min(max(limit, 1), 100))
        return {"ok": True, "items": items}

    @app.get("/ops/status", dependencies=[Depends(require_api_key)], tags=["Ops"])
    async def ops_status() -> Dict[str, Any]:
        """Return latest backup, rollback, failover, and smoke summaries."""
        return ops_status_service.status()

    @app.get("/cloth/orders", dependencies=[Depends(require_api_key)], tags=["E-Commerce"])
    async def cloth_orders(customer_id: str | None = None, limit: int = 10) -> Dict[str, Any]:
        """List CLOTH orders from the configured e-commerce provider."""
        items = orders_service.list_orders(customer_id=customer_id, limit=min(max(limit, 1), 100))
        for item in items:
            order_key = str(item.get("order_id") or item.get("id") or item.get("order_number") or "")
            if order_key:
                memory_store.save_memory(["buyeros", "orders"], order_key, {"project_id": "commerce", **item}, created_by="orders_service")
        return {"ok": True, "items": items, "configured": orders_service.configured()}

    @app.get("/cloth/orders/{order_id}", dependencies=[Depends(require_api_key)], tags=["E-Commerce"])
    async def cloth_order_get(order_id: str) -> Dict[str, Any]:
        """Return one CLOTH order from the configured e-commerce provider."""
        order = orders_service.get_order(order_id)
        ok = not bool(order.get("error"))
        if ok:
            memory_store.save_memory(["buyeros", "orders"], order_id, {"project_id": "commerce", **order}, created_by="orders_service")
        return {"ok": ok, "order": order, "configured": orders_service.configured()}

    @app.post("/automation/daily-report", dependencies=[Depends(require_api_key)], tags=["Automation"])
    async def automation_daily_report(payload: DailyReportRequest) -> Dict[str, Any]:
        """Create a daily operations report from current BuyerOS memory."""
        result = business_automation.create_daily_report(date=payload.date)
        audit_logger.log(action="automation.daily_report", actor="api", details=result)
        return result

    @app.post("/automation/ocr-posting", dependencies=[Depends(require_api_key)], tags=["Automation"])
    async def automation_ocr_posting(payload: OcrPostingRequest) -> Dict[str, Any]:
        """Create an accounting entry from OCR text."""
        result = business_automation.post_ocr_entry(
            text=payload.text,
            source=payload.source,
            entry_id=payload.entry_id,
        )
        audit_logger.log(action="automation.ocr_posting", actor="api", details=result)
        automation_runs_total.labels(workflow="ocr_posting").inc()
        return result

    @app.post("/automation/reconcile", dependencies=[Depends(require_api_key)], tags=["Automation"])
    async def automation_reconcile(payload: ReconcileRequest) -> Dict[str, Any]:
        """Compare expected and actual totals and create an alert on mismatch."""
        result = business_automation.reconcile_entries(
            expected_total=payload.expected_total,
            actual_total=payload.actual_total,
            reference=payload.reference,
        )
        audit_logger.log(action="automation.reconcile", actor="api", details=result)
        automation_runs_total.labels(workflow="reconcile").inc()
        return result

    @app.post("/automation/alerts", dependencies=[Depends(require_api_key)], tags=["Automation"])
    async def automation_alerts(payload: AlertsRequest) -> Dict[str, Any]:
        """Generate anomaly alerts for items above a threshold."""
        result = business_automation.generate_alerts(
            items=[item.model_dump() for item in payload.items],
            threshold=payload.threshold,
        )
        audit_logger.log(action="automation.alerts", actor="api", details=result)
        automation_runs_total.labels(workflow="alerts").inc()
        return result

    @app.post("/automation/approval", dependencies=[Depends(require_api_key)], tags=["Automation"])
    async def automation_approval(payload: ApprovalRequest) -> Dict[str, Any]:
        """Create a manual approval task."""
        result = business_automation.request_approval(
            task_id=payload.task_id,
            reason=payload.reason,
            payload=payload.payload,
        )
        audit_logger.log(action="automation.approval", actor="api", details=result)
        automation_runs_total.labels(workflow="approval").inc()
        return result

    @app.post("/automation/retry", dependencies=[Depends(require_api_key)], tags=["Automation"])
    async def automation_retry(payload: RetryRequest) -> Dict[str, Any]:
        """Record retry state for an automation task."""
        result = business_automation.record_retry(
            task_id=payload.task_id,
            error=payload.error,
            attempt=payload.attempt,
        )
        audit_logger.log(action="automation.retry", actor="api", details=result)
        automation_runs_total.labels(workflow="retry").inc()
        return result

    @app.post("/automation/close-cycle", dependencies=[Depends(require_api_key)], tags=["Automation"])
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
        automation_runs_total.labels(workflow="close_cycle").inc()
        return result

    @app.post("/reports/create", dependencies=[Depends(require_api_key)], tags=["Reports"])
    async def reports_create(payload: ReportCreateRequest) -> Dict[str, Any]:
        """Create a buyer report snapshot."""
        result = reporting_service.create_report(period=payload.period, date=payload.date)
        audit_logger.log(action="reports.create", actor="api", details={"period": payload.period, "date": payload.date})
        return result

    @app.get("/reports/history", dependencies=[Depends(require_api_key)], tags=["Reports"])
    async def reports_history(limit: int = 20) -> Dict[str, Any]:
        """Return report history."""
        return reporting_service.history(limit=min(max(limit, 1), 100))

    @app.post("/reports/export", dependencies=[Depends(require_api_key)], tags=["Reports"])
    async def reports_export(payload: ReportExportRequest) -> Dict[str, Any]:
        """Export report history as CSV text."""
        return reporting_service.export_csv(report_id=payload.report_id, limit=payload.limit)

    @app.post("/promo/campaigns", dependencies=[Depends(require_api_key)], tags=["Promo"])
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

    @app.get("/promo/campaigns", dependencies=[Depends(require_api_key)], tags=["Promo"])
    async def promo_campaigns_list(limit: int = 20) -> Dict[str, Any]:
        """List XAU promo campaigns."""
        return promo_service.list_campaigns(limit=min(max(limit, 1), 100))

    @app.post("/promo/events", dependencies=[Depends(require_api_key)], tags=["Promo"])
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

    @app.get("/promo/metrics", dependencies=[Depends(require_api_key)], tags=["Promo"])
    async def promo_metrics(campaign_id: str | None = None) -> Dict[str, Any]:
        """Return XAU promo metrics."""
        return promo_service.metrics(campaign_id=campaign_id)

    @app.post("/tasks", dependencies=[Depends(require_api_key)], tags=["Tasks"])
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

    @app.get("/tasks", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_list(lane: str | None = None, limit: int = 50) -> Dict[str, Any]:
        """List AI company OS task board items."""
        return task_board_service.list_tasks(lane=lane, limit=min(max(limit, 1), 100))

    @app.post("/tasks/{task_id}/status", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_status(task_id: str, payload: TaskStatusRequest) -> Dict[str, Any]:
        """Update task status."""
        return task_board_service.update_status(task_id=task_id, status=payload.status, note=payload.note)

    @app.post("/tasks/{task_id}/run", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_run(task_id: str, payload: TaskRunRequest) -> Dict[str, Any]:
        """Record a task run result."""
        return task_board_service.run_task(task_id=task_id, result=payload.result, provider=payload.provider)

    @app.get("/tasks/{task_id}", dependencies=[Depends(require_api_key)], tags=["Tasks"])
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

    @app.post("/tasks/dispatch", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_dispatch(payload: TaskDispatchRequest) -> Dict[str, Any]:
        """Create a task and dispatch it to the provider layer (single-hop)."""
        try:
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
                agent_runs_total.labels(agent=payload.preferred_provider or "openai", status="success").inc()
            else:
                task_board_service.update_status(task_id=task_id, status="blocked", note=str(result.get("error") or "provider_failed"))
                agent_runs_total.labels(agent=payload.preferred_provider or "openai", status="blocked").inc()
            audit_logger.log(
                action="tasks.dispatch",
                actor="api",
                details={"task_id": task_id, "project": project, "task_type": payload.task_type, "provider": result.get("provider"), "ok": bool(result.get("ok"))},
            )
            return {"ok": True, "task_id": task_id, "result": result}
        except Exception as exc:
            _log.error("tasks_dispatch_failed", error=str(exc), exc_info=True)
            if sentry_dsn:
                capture_exception(exc)
            raise

    @app.post("/tasks/dispatch_plan", dependencies=[Depends(require_api_key)], tags=["Tasks"])
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

    @app.get("/tasks/{task_id}/subtasks", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_subtasks(task_id: str, limit: int = 50) -> Dict[str, Any]:
        """List subtasks for a task."""
        return dispatcher_service.list_subtasks(task_id=task_id, limit=min(max(limit, 1), 200))

    @app.post("/tasks/{task_id}/subtasks/run", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_subtasks_run(task_id: str, payload: SubtaskRunRequest) -> Dict[str, Any]:
        """Run a specific subtask."""
        return dispatcher_service.run_subtask(
            task_id=task_id,
            subtask_id=payload.subtask_id,
            preferred_provider=payload.preferred_provider,
            session_id=payload.session_id or f"task-{task_id}",
        )

    @app.post("/tasks/{task_id}/subtasks/next", dependencies=[Depends(require_api_key)], tags=["Tasks"])
    async def tasks_subtasks_next(task_id: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Run next queued subtask."""
        preferred = (payload or {}).get("preferred_provider") if isinstance(payload, dict) else None
        session_id = (payload or {}).get("session_id") if isinstance(payload, dict) else None
        return dispatcher_service.run_next(task_id=task_id, preferred_provider=preferred, session_id=session_id)

    @app.post("/tasks/{task_id}/run_all", dependencies=[Depends(require_api_key)], tags=["Tasks"])
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

    # ──────────────────────────────────────────────────────────────────
    # Expense Claims — 買手報帳系統
    # ──────────────────────────────────────────────────────────────────

    @app.post("/expenses", dependencies=[Depends(require_api_key)], tags=["Expenses"])
    async def submit_expense(request: Request) -> Dict[str, Any]:
        """Submit a new expense claim (status=pending)."""
        body = await request.json()
        svc: ExpenseService = request.app.state.expense_service
        try:
            claim = svc.submit(
                buyer_name=body.get("buyer_name", ""),
                amount=float(body.get("amount", 0)),
                description=body.get("description", ""),
                currency=body.get("currency", "HKD"),
                category=body.get("category", "other"),
                receipt_url=body.get("receipt_url"),
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        audit_logger.log(action="expenses.submit", actor="api",
                         details={"id": claim["id"], "buyer": claim["buyer_name"],
                                  "amount": claim["amount"]})
        return {"ok": True, "claim": claim}

    @app.get("/expenses", dependencies=[Depends(require_api_key)], tags=["Expenses"])
    async def list_expenses(
        request: Request,
        status: Optional[str] = None,
        buyer_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List expense claims with optional status / buyer filter."""
        svc: ExpenseService = request.app.state.expense_service
        try:
            claims = svc.list_claims(status=status, buyer_name=buyer_name,
                                     limit=limit, offset=offset)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return {"ok": True, "claims": claims, "count": len(claims)}

    @app.get("/expenses/export/csv", dependencies=[Depends(require_api_key)], tags=["Expenses"])
    async def export_expenses_csv(
        request: Request,
        status: Optional[str] = None,
        buyer_name: Optional[str] = None,
    ) -> Response:
        """Export expense claims as CSV download."""
        svc: ExpenseService = request.app.state.expense_service
        try:
            csv_content = svc.export_csv(status=status, buyer_name=buyer_name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )

    @app.get("/expenses/{claim_id}", dependencies=[Depends(require_api_key)], tags=["Expenses"])
    async def get_expense(request: Request, claim_id: str) -> Dict[str, Any]:
        """Fetch a single expense claim by ID."""
        svc: ExpenseService = request.app.state.expense_service
        claim = svc.get_claim(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="claim not found")
        return {"ok": True, "claim": claim}

    @app.patch("/expenses/{claim_id}/status", dependencies=[Depends(require_api_key)], tags=["Expenses"])
    async def update_expense_status(request: Request, claim_id: str) -> Dict[str, Any]:
        """Approve or reject an expense claim."""
        body = await request.json()
        new_status = body.get("status", "")
        if new_status not in {"approved", "rejected"}:
            raise HTTPException(status_code=422, detail="status must be 'approved' or 'rejected'")
        svc: ExpenseService = request.app.state.expense_service
        claim = svc.update_status(
            claim_id=claim_id,
            new_status=new_status,
            reviewer=body.get("reviewer"),
            reviewer_note=body.get("reviewer_note"),
        )
        if not claim:
            raise HTTPException(status_code=404, detail="claim not found")
        audit_logger.log(action=f"expenses.{new_status}", actor="api",
                         details={"id": claim_id, "reviewer": body.get("reviewer")})
        return {"ok": True, "claim": claim}

    @app.get("/system/capabilities", dependencies=[Depends(require_api_key)], tags=["Meta"])
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
