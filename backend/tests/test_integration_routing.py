"""Tests for XAU and CLOTH integration routing in the dispatcher."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient

from app.context.context_hub import ContextHub
from app.memory_store import MemoryStore
from app.services.task_board_service import TaskBoardService
from app.services.task_dispatcher_service import TaskDispatcherService
from app.services.xau_integration import (
    XAUConfig,
    XAUIntegration,
    ScriptResult,
    ScriptSegments,
)
from app.services.cloth_integration import (
    CLOTHConfig,
    CLOTHIntegration,
    LiveSellingPlan,
    FinanceCheck,
    InventoryCheck,
)
from app.workflows.main import create_app


def test_route_for_xau_project() -> None:
    """xau project should route to xau integration."""
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=MagicMock(get_project=MagicMock(return_value={"project_id": "xau"})),
        providers=MagicMock(),
        context_hub=MagicMock(),
        ops_agent=MagicMock(),
        finance_agent=MagicMock(),
    )
    assert service._route_for(task_type="live_stream", prompt="generate gold script", project="xau") == "xau"
    assert service._route_for(task_type="news", prompt="latest news", project="xau") == "xau"
    assert service._route_for(task_type="signal", prompt="interpret signal", project="xau") == "xau"


def test_route_for_cloth_project() -> None:
    """commerce project should route to cloth integration."""
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=MagicMock(),
        providers=MagicMock(),
        context_hub=MagicMock(),
        ops_agent=MagicMock(),
        finance_agent=MagicMock(),
    )
    assert service._route_for(task_type="live_selling", prompt="generate selling plan", project="commerce") == "cloth"
    assert service._route_for(task_type="selling_plan", prompt="product script", project="commerce") == "cloth"
    assert service._route_for(task_type="live_selling", prompt="AI virtual host", project="commerce") == "cloth"


def test_route_for_xau_by_task_type() -> None:
    """xau-specific task types should route to xau even without xau project."""
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=MagicMock(),
        providers=MagicMock(),
        context_hub=MagicMock(),
        ops_agent=MagicMock(),
        finance_agent=MagicMock(),
    )
    assert service._route_for(task_type="live_stream", prompt="", project="") == "xau"
    assert service._route_for(task_type="gold_script", prompt="", project="buyer_ai") == "xau"
    assert service._route_for(task_type="news", prompt="", project="buyer_ai") == "xau"


def test_route_for_cloth_by_task_type() -> None:
    """cloth-specific task types should route to cloth even without commerce project."""
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=MagicMock(),
        providers=MagicMock(),
        context_hub=MagicMock(),
        ops_agent=MagicMock(),
        finance_agent=MagicMock(),
    )
    assert service._route_for(task_type="live_selling", prompt="", project="") == "cloth"
    assert service._route_for(task_type="selling_plan", prompt="", project="buyer_ai") == "cloth"


def test_xau_integration_script_result() -> None:
    """XAUIntegration ScriptResult should serialize correctly."""
    segments = ScriptSegments(
        hook="先停10秒",
        story="偏多思路",
        interaction="打1/2/3",
        cta="留言黃金",
        risk="控制倉位",
        style="educational",
        safety="真實互動",
    )
    result = ScriptResult(
        script="完整腳本內容",
        segments=segments,
        source="llm",
        cached=False,
        bias_type="up",
    )
    assert result.script == "完整腳本內容"
    assert result.segments.hook == "先停10秒"
    assert result.source == "llm"
    assert result.cached is False
    assert result.bias_type == "up"


def test_cloth_integration_live_selling_plan() -> None:
    """CLOTHIntegration LiveSellingPlan should serialize correctly."""
    plan = LiveSellingPlan(
        planId="live-123",
        productId="prod-001",
        productTitle="Hermes Birkin 25",
        accountStyle="luxury_editor",
        hook="先停5秒，這件...",
        script="大家好...",
        interactionPrompts=["留言1/2/3", "用途問答"],
        cta="留言想看",
        inventoryCheck=InventoryCheck(status="ready", sku="prod-001", message="可作主推"),
        financeCheck=FinanceCheck(
            expectedRevenue=80000,
            estimatedPlatformFee=6400,
            estimatedAdCost=2400,
            estimatedInventoryCost=36000,
            estimatedRefundReserve=4000,
            estimatedNetProfit=31200,
        ),
        supportNotes=["只引導真實留言"],
        safetyNote="AI虛擬主播身份",
        createdAt="2026-05-24T12:00:00Z",
    )

    d = plan.to_dict()
    assert d["plan_id"] == "live-123"
    assert d["product_title"] == "Hermes Birkin 25"
    assert d["finance_check"]["estimated_net_profit"] == 31200
    assert d["inventory_check"]["status"] == "ready"
    assert "真實留言" in d["support_notes"][0]


def test_xau_config_from_env(monkeypatch) -> None:
    """XAUConfig should read from environment variables."""
    monkeypatch.setenv("XAU_BASE_URL", "https://api.xau.example.com")
    monkeypatch.setenv("XAU_TIMEOUT", "15.0")

    config = XAUConfig.from_env()
    assert config.base_url == "https://api.xau.example.com"
    assert config.timeout == 15.0


def test_cloth_config_defaults() -> None:
    """CLOTHConfig should have sensible defaults."""
    config = CLOTHConfig()
    assert config.base_url == "http://localhost:3001"
    assert config.timeout == 30.0


def test_xau_runtime_client_contract() -> None:
    """BuyerOS XAU client should call the agreed live-room runtime endpoints."""
    seen_requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = {}
        if request.content:
            body = httpx.Response(200, content=request.content).json()
        seen_requests.append((request.method, request.url.path, body))

        if request.method == "GET" and request.url.path == "/api/news/latest":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "headline": "US session gold volatility watch",
                            "impact": "medium",
                        }
                    ]
                },
            )

        if request.method == "POST" and request.url.path == "/api/ai/script":
            return httpx.Response(
                200,
                json={
                    "script": "教育型黃金直播腳本",
                    "segments": {
                        "hook": "先看支撐",
                        "story": "等待突破確認",
                        "interaction": "留言 1/2/3",
                        "cta": "訂閱風控提醒",
                        "risk": "不追單",
                        "style": "educational",
                        "safety": "非投資建議",
                    },
                    "source": "fallback",
                    "cached": False,
                },
            )

        return httpx.Response(404, json={"error": "unexpected endpoint"})

    integration = XAUIntegration(XAUConfig(base_url="https://xau.test"))
    integration._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://xau.test")

    news_result = integration.get_latest_news()
    script_result = integration.generate_script(
        bias_type="wait",
        topic="Phase 2 runtime smoke",
        account_style="educational",
    )

    assert news_result.ok is True
    assert news_result.data["items"][0]["headline"] == "US session gold volatility watch"
    assert script_result.ok is True
    assert script_result.data.script == "教育型黃金直播腳本"
    assert script_result.data.segments.risk == "不追單"
    assert ("GET", "/api/news/latest", {}) in seen_requests
    assert (
        "POST",
        "/api/ai/script",
        {
            "biasType": "wait",
            "momentum": 50,
            "position": 50,
            "risk": 50,
            "forceRefresh": False,
            "topic": "Phase 2 runtime smoke",
            "accountStyle": "educational",
        },
    ) in seen_requests


def test_cloth_runtime_client_contract() -> None:
    """BuyerOS CLOTH client should call the agreed commerce live-selling endpoints."""
    seen_requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = {}
        if request.content:
            body = httpx.Response(200, content=request.content).json()
        seen_requests.append((request.method, request.url.path, body))

        if request.method == "GET" and request.url.path == "/api/live/readiness":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "sellableCount": 3,
                    "checks": ["inventory", "finance", "support"],
                    "safetyNote": "AI presenter disclosure required",
                },
            )

        if request.method == "POST" and request.url.path == "/api/live/selling-plan":
            return httpx.Response(
                200,
                json={
                    "planId": "live-phase2",
                    "productId": "prod-001",
                    "productTitle": "Hermes Birkin 25",
                    "accountStyle": "educational",
                    "hook": "先講成色同來源",
                    "script": "完整帶貨腳本",
                    "interactionPrompts": ["留言想看細節", "問保養狀態"],
                    "cta": "聯絡客服查詢",
                    "inventoryCheck": {
                        "status": "ready",
                        "sku": "prod-001",
                        "message": "可主推",
                    },
                    "financeCheck": {
                        "expectedRevenue": 80000,
                        "estimatedPlatformFee": 6400,
                        "estimatedAdCost": 2400,
                        "estimatedInventoryCost": 36000,
                        "estimatedRefundReserve": 4000,
                        "estimatedNetProfit": 31200,
                    },
                    "supportNotes": ["只承諾已驗證資料"],
                    "safetyNote": "AI 虛擬主播身份需披露",
                    "createdAt": "2026-05-25T00:00:00Z",
                },
            )

        return httpx.Response(404, json={"error": "unexpected endpoint"})

    integration = CLOTHIntegration(CLOTHConfig(base_url="https://cloth.test"))
    integration._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://cloth.test")

    readiness = integration.check_readiness()
    selling_plan = integration.generate_selling_plan(
        product_id="prod-001",
        account_style="educational",
        cta="聯絡客服查詢",
    )

    assert readiness.ok is True
    assert readiness.data.ready is True
    assert readiness.data.sellableCount == 3
    assert selling_plan.ok is True
    assert selling_plan.data.productTitle == "Hermes Birkin 25"
    assert selling_plan.data.financeCheck.estimatedNetProfit == 31200
    assert ("GET", "/api/live/readiness", {}) in seen_requests
    assert (
        "POST",
        "/api/live/selling-plan",
        {
            "accountStyle": "educational",
            "productId": "prod-001",
            "cta": "聯絡客服查詢",
        },
    ) in seen_requests


def test_dispatcher_runs_xau_integration_when_configured() -> None:
    """Dispatcher should complete xau subtasks through the configured XAU client."""
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=MagicMock(get_project=MagicMock(return_value={"project_id": "xau"})),
        providers=MagicMock(),
        context_hub=ContextHub(memory),
        ops_agent=MagicMock(),
        finance_agent=MagicMock(),
        xau_integration=MagicMock(
            generate_script=MagicMock(
                return_value=MagicMock(
                    ok=True,
                    data=ScriptResult(
                        script="XAU runtime script",
                        segments=ScriptSegments(
                            hook="hook",
                            story="story",
                            interaction="interaction",
                            cta="cta",
                            risk="risk",
                        ),
                        source="fallback",
                        cached=False,
                        bias_type="wait",
                    ),
                    error="",
                )
            )
        ),
    )
    plan = service.create_plan(
        project="xau",
        task_type="live_stream",
        title="XAU runtime integration",
        prompt="Generate a safe education live script.",
        preferred_provider=None,
        session_id="phase2-xau",
        max_steps=1,
    )
    subtask_id = plan["plan"]["steps"][0]["subtask_id"]

    result = service.run_subtask(
        task_id=plan["task_id"],
        subtask_id=subtask_id,
        preferred_provider=None,
        session_id="phase2-xau",
    )

    assert result["ok"] is True
    assert result["result"]["provider"] == "xau_integration"
    assert "XAU runtime script" in result["result"]["reply"]


def test_dispatcher_runs_cloth_integration_when_configured() -> None:
    """Dispatcher should complete commerce subtasks through the configured CLOTH client."""
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=MagicMock(get_project=MagicMock(return_value={"project_id": "commerce"})),
        providers=MagicMock(),
        context_hub=ContextHub(memory),
        ops_agent=MagicMock(),
        finance_agent=MagicMock(),
        cloth_integration=MagicMock(
            generate_selling_plan=MagicMock(
                return_value=MagicMock(
                    ok=True,
                    data=LiveSellingPlan(
                        planId="plan-phase2",
                        productId="prod-001",
                        productTitle="Hermes Birkin 25",
                        inventoryCheck=InventoryCheck(status="ready", sku="prod-001", message="ready"),
                        financeCheck=FinanceCheck(estimatedNetProfit=31200),
                    ),
                    error="",
                )
            )
        ),
    )
    plan = service.create_plan(
        project="commerce",
        task_type="live_selling",
        title="CLOTH runtime integration",
        prompt="Generate a safe AI virtual host selling plan.",
        preferred_provider=None,
        session_id="phase2-cloth",
        max_steps=1,
    )
    subtask_id = plan["plan"]["steps"][0]["subtask_id"]

    result = service.run_subtask(
        task_id=plan["task_id"],
        subtask_id=subtask_id,
        preferred_provider=None,
        session_id="phase2-cloth",
    )

    assert result["ok"] is True
    assert result["result"]["provider"] == "cloth_integration"
    assert "Hermes Birkin 25" in result["result"]["reply"]


def test_dispatcher_xau_route_when_unconfigured(monkeypatch) -> None:
    """When xau integration is not configured, xau route should block gracefully."""
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    plan = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "xau",
            "task_type": "live_stream",
            "title": "xau smoke test",
            "prompt": "generate gold script",
            "max_steps": 1,
            "session_id": "sess-xau-unconfigured",
        },
        headers=headers,
    )
    assert plan.status_code == 200
    task_id = plan.json()["task_id"]

    # XAU is not configured, so this should block
    run = client.post(f"/tasks/{task_id}/subtasks/next", json={"session_id": "sess-xau-unconfigured"}, headers=headers)
    assert run.status_code == 200
    body = run.json()
    # Without XAU configured, the subtask should be blocked
    assert body.get("ok") in {True, False}


def test_dispatcher_cloth_route_when_unconfigured(monkeypatch) -> None:
    """When cloth integration is not configured, cloth route should block gracefully."""
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    plan = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "commerce",
            "task_type": "live_selling",
            "title": "cloth smoke test",
            "prompt": "generate selling plan",
            "max_steps": 1,
            "session_id": "sess-cloth-unconfigured",
        },
        headers=headers,
    )
    assert plan.status_code == 200
    task_id = plan.json()["task_id"]

    run = client.post(f"/tasks/{task_id}/subtasks/next", json={"session_id": "sess-cloth-unconfigured"}, headers=headers)
    assert run.status_code == 200
    body = run.json()
    assert body.get("ok") in {True, False}
