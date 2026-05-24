from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.memory_store import MemoryStore
from app.services.task_board_service import TaskBoardService
from app.services.task_dispatcher_service import TaskDispatcherService
from app.workflows.main import create_app


def test_command_center_p0_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    projects = client.get("/projects", headers=headers)
    team = client.get("/ai-team/status", headers=headers)
    timeline = client.post("/memory/timeline", json={"limit": 10}, headers=headers)
    dispatch = client.post(
        "/tasks/dispatch",
        json={
            "project": "buyer_ai",
            "task_type": "planning",
            "title": "P0 reset sanity",
            "prompt": "Summarize the next three steps for BuyerOS P0 reset.",
            "preferred_provider": "openai",
            "session_id": "sess-test",
        },
        headers=headers,
    )

    assert projects.status_code == 200
    assert projects.json()["ok"] is True
    assert team.status_code == 200
    assert team.json()["ok"] is True
    assert timeline.status_code == 200
    assert timeline.json()["ok"] is True
    assert dispatch.status_code == 200
    assert dispatch.json()["ok"] is True
    assert dispatch.json()["task_id"]

    task_id = dispatch.json()["task_id"]
    detail = client.get(f"/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["ok"] is True

    plan = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "buyer_ai",
            "task_type": "code",
            "title": "plan test",
            "prompt": "Create a plan for refactor.",
            "max_steps": 3,
        },
        headers=headers,
    )
    assert plan.status_code == 200
    body = plan.json()
    assert body["ok"] is True
    planned_task_id = body["task_id"]
    subtasks = client.get(f"/tasks/{planned_task_id}/subtasks", headers=headers)
    assert subtasks.status_code == 200
    assert subtasks.json()["ok"] is True

    first_run = client.post(
        f"/tasks/{planned_task_id}/subtasks/next",
        json={"preferred_provider": "openai", "session_id": "sess-test"},
        headers=headers,
    )
    second_run = client.post(
        f"/tasks/{planned_task_id}/subtasks/next",
        json={"preferred_provider": "openai", "session_id": "sess-test"},
        headers=headers,
    )
    third_run = client.post(
        f"/tasks/{planned_task_id}/subtasks/next",
        json={"preferred_provider": "openai", "session_id": "sess-test"},
        headers=headers,
    )
    final_run = client.post(
        f"/tasks/{planned_task_id}/subtasks/next",
        json={"preferred_provider": "openai", "session_id": "sess-test"},
        headers=headers,
    )
    refreshed = client.get(f"/tasks/{planned_task_id}/subtasks", headers=headers)

    for response in [first_run, second_run, third_run, final_run, refreshed]:
        assert response.status_code == 200
        assert response.json()["ok"] is True
    assert final_run.json()["status"] == "no_pending_subtasks"
    assert all((item["content"] or {})["status"] == "completed" for item in refreshed.json()["items"])


def test_dispatcher_routing_ops_finance(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    # Ensure provider layer is not invoked for ops/finance task types.
    dispatcher = client.app.state.dispatcher_service
    called = {"providers_run": 0}

    def _spy_run(**kwargs):
        called["providers_run"] += 1
        return {"ok": False, "provider": "spy", "reply": "should_not_be_called"}

    monkeypatch.setattr(dispatcher.providers, "run", _spy_run)

    # Ops path
    plan = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "buyer_ai",
            "task_type": "refund",
            "title": "refund test",
            "prompt": "退款 991",
            "max_steps": 2,
            "session_id": "sess-ops",
        },
        headers=headers,
    )
    assert plan.status_code == 200
    task_id = plan.json()["task_id"]
    next_run = client.post(f"/tasks/{task_id}/subtasks/next", json={"session_id": "sess-ops"}, headers=headers)
    assert next_run.status_code == 200
    body = next_run.json()
    assert body["ok"] in {True, False}
    assert called["providers_run"] == 0

    # Finance path
    plan2 = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "buyer_ai",
            "task_type": "profit",
            "title": "finance test",
            "prompt": "profit for order 123",
            "max_steps": 2,
            "session_id": "sess-fin",
        },
        headers=headers,
    )
    assert plan2.status_code == 200
    task_id2 = plan2.json()["task_id"]
    next_run2 = client.post(f"/tasks/{task_id2}/subtasks/next", json={"session_id": "sess-fin"}, headers=headers)
    assert next_run2.status_code == 200
    assert called["providers_run"] == 0


def test_run_all_runs_until_done(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    plan = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "buyer_ai",
            "task_type": "refund",
            "title": "run_all test",
            "prompt": "退款 991",
            "max_steps": 2,
            "session_id": "sess-runall",
        },
        headers=headers,
    )
    assert plan.status_code == 200
    task_id = plan.json()["task_id"]

    run_all = client.post(f"/tasks/{task_id}/run_all", json={"session_id": "sess-runall", "max_steps": 10}, headers=headers)
    assert run_all.status_code == 200
    body = run_all.json()
    assert body["status"] in {"completed", "blocked", "max_steps_exceeded"}
    assert "results" in body
    assert "blocked_reason" in body
    replies = [
        (item.get("result") or {}).get("reply", "")
        for item in body["results"]
        if isinstance(item.get("result"), dict) and (item.get("result") or {}).get("reply")
    ]
    assert replies
    assert all("991" in reply for reply in replies)
    assert not any("sub-" in reply for reply in replies)

    timeline = client.post(
        "/memory/timeline",
        json={"project_id": "buyer_ai", "session_id": "sess-runall", "limit": 50},
        headers=headers,
    )
    assert timeline.status_code == 200
    assert any((item.get("namespace") or []) == ["buyeros", "run_all"] for item in timeline.json()["items"])


def test_dispatcher_live_selling_routes_to_cloth_and_records_timeline(monkeypatch) -> None:
    """commerce + live_selling now routes to CLOTH integration (not provider)."""
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    dispatcher = client.app.state.dispatcher_service

    # Mock CLOTH integration to return a successful plan
    mock_cloth_result = MagicMock()
    mock_cloth_result.ok = True
    mock_cloth_result.data = MagicMock()
    mock_cloth_result.data.productTitle = "Test Product"
    mock_cloth_result.data.financeCheck = MagicMock()
    mock_cloth_result.data.financeCheck.estimatedNetProfit = 5000
    mock_cloth_result.data.to_dict = lambda: {"plan_id": "test", "product_title": "Test Product"}
    mock_cloth_result.error = ""

    mock_cloth = MagicMock()
    mock_cloth.generate_selling_plan.return_value = mock_cloth_result
    dispatcher.cloth = mock_cloth

    # Mock context_hub.write_context to actually save the routing record to memory
    # (cloth integration writes to context, which stores to memory_store)
    memory_store = client.app.state.memory_store
    context_hub = client.app.state.context_hub
    real_write = context_hub.write_context

    def mock_write(**kw):
        real_write(**kw)
        # Manually save the routing record to memory so timeline can find it
        content = kw.get("content", {})
        if content.get("route") in ("cloth", "xau"):
            memory_store.save_memory(
                ["buyeros", "routing"],
                kw.get("session_id", "") + "-routing",
                content,
                created_by=kw.get("created_by", "dispatcher"),
            )

    context_hub.write_context = mock_write

    plan = client.post(
        "/tasks/dispatch_plan",
        json={
            "project": "commerce",
            "task_type": "live_selling",
            "title": "AI live selling smoke",
            "prompt": "Plan one AI virtual host livestream selling flow with inventory and finance checks.",
            "max_steps": 3,
            "session_id": "sess-live-selling",
        },
        headers=headers,
    )
    assert plan.status_code == 200
    assert plan.json()["plan"]["project"] == "commerce"
    assert [step["kind"] for step in plan.json()["plan"]["steps"]] == ["collect", "plan", "verify"]

    task_id = plan.json()["task_id"]
    run_all = client.post(f"/tasks/{task_id}/run_all", json={"session_id": "sess-live-selling"}, headers=headers)
    assert run_all.status_code == 200
    assert run_all.json()["status"] == "completed"

    timeline = client.post(
        "/memory/timeline",
        json={"project_id": "commerce", "session_id": "sess-live-selling", "limit": 50},
        headers=headers,
    )
    assert timeline.status_code == 200
    namespaces = [item.get("namespace") for item in timeline.json()["items"]]
    assert ["buyeros", "run_all"] in namespaces

    # Verify CLOTH was called
    assert mock_cloth.generate_selling_plan.called


def test_list_subtasks_dedupes_latest_state() -> None:
    memory = MemoryStore()
    service = TaskDispatcherService(
        memory_store=memory,
        task_board=TaskBoardService(memory),
        projects=object(),  # type: ignore[arg-type]
        providers=object(),  # type: ignore[arg-type]
        context_hub=object(),  # type: ignore[arg-type]
        ops_agent=object(),  # type: ignore[arg-type]
        finance_agent=object(),  # type: ignore[arg-type]
    )

    memory.memory.append(
        {
            "namespace": ["buyeros", "subtasks"],
            "memory_key": "sub-1",
            "content": {"subtask_id": "sub-1", "task_id": "task-1", "order": 1, "status": "queued"},
            "created_at": "2026-05-22T10:00:00+00:00",
        }
    )
    memory.memory.append(
        {
            "namespace": ["buyeros", "subtasks"],
            "memory_key": "sub-1",
            "content": {"subtask_id": "sub-1", "task_id": "task-1", "order": 1, "status": "completed"},
            "created_at": "2026-05-22T10:01:00+00:00",
        }
    )

    items = service.list_subtasks(task_id="task-1")["items"]

    assert len(items) == 1
    assert items[0]["content"]["status"] == "completed"
