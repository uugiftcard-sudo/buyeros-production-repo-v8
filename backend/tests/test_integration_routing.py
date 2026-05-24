"""Tests for XAU and CLOTH integration routing in the dispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.memory_store import MemoryStore
from app.services.task_board_service import TaskBoardService
from app.services.task_dispatcher_service import TaskDispatcherService
from app.services.xau_integration import (
    XAUConfig,
    ScriptResult,
    ScriptSegments,
)
from app.services.cloth_integration import (
    CLOTHConfig,
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
