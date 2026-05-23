from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.memory_store import MemoryStore
from app.services.project_registry_service import ProjectRegistryService
from app.services.promo_service import PromoService
from app.services.reporting_service import ReportingService
from app.services.task_board_service import TaskBoardService
from app.workflows.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_reporting_service_creates_history_and_csv() -> None:
    memory = MemoryStore()
    memory.save_memory(["buyeros", "refunds"], "991", {"result": "done"}, created_by="test")
    service = ReportingService(memory)

    created = service.create_report(period="daily", date="2026-05-22")
    history = service.history()
    exported = service.export_csv(report_id="daily-2026-05-22")

    assert created["ok"] is True
    assert created["report"]["counts"]["refunds"] == 1
    assert history["items"]
    assert "daily-2026-05-22" in exported["content"]


def test_promo_service_campaign_event_metrics() -> None:
    memory = MemoryStore()
    service = PromoService(memory)

    campaign = service.create_campaign(name="XAU May Promo", offer="Gold promo", budget_hkd=500)
    campaign_id = campaign["campaign"]["campaign_id"]
    service.record_event(campaign_id=campaign_id, event_type="view", source="test")
    service.record_event(campaign_id=campaign_id, event_type="conversion", value_hkd=1288, source="test")
    metrics = service.metrics(campaign_id=campaign_id)

    assert campaign["ok"] is True
    assert metrics["counts"]["view"] == 1
    assert metrics["counts"]["conversion"] == 1
    assert metrics["revenue_hkd"] == 1288


def test_task_board_service_lifecycle() -> None:
    memory = MemoryStore()
    service = TaskBoardService(memory)

    task = service.create_task(title="補 XAU promo", lane="promo", owner_provider="claude")
    task_id = task["task"]["task_id"]
    status = service.update_status(task_id=task_id, status="running", note="started")
    run = service.run_task(task_id=task_id, result="done", provider="claude")
    tasks = service.list_tasks(lane="promo")

    assert task["task"]["lane_label"] == "XAU 中控"
    assert status["task"]["status"] == "running"
    assert run["run"]["status"] == "completed"
    assert tasks["items"]


def test_task_board_accepts_three_workspace_lanes_and_legacy_aliases() -> None:
    memory = MemoryStore()
    service = TaskBoardService(memory)

    report = service.create_task(title="買手 report", lane="report", owner_provider="openai")
    commerce = service.create_task(title="整理 CLOTH SOP", lane="commerce", owner_provider="claude")
    xau = service.create_task(title="整理 XAU promo", lane="xau", owner_provider="openai")
    buyeros = service.create_task(title="AI team core", lane="buyeros", owner_provider="openai")
    buyeros_alias = service.create_task(title="BuyerOS alias", lane="ai_team", owner_provider="openai")
    buyeros_alias_dash = service.create_task(title="BuyerOS alias dash", lane="ai-solo-team", owner_provider="openai")
    xau_alias = service.create_task(title="XAU alias", lane="xau-team", owner_provider="openai")
    cloth_alias = service.create_task(title="CLOTH alias", lane="cloth", owner_provider="openai")

    assert report["task"]["lane"] == "cloth"
    assert report["task"]["lane_label"] == "CLOTH 網店自動系統"
    assert commerce["task"]["lane"] == "cloth"
    assert commerce["task"]["lane_label"] == "CLOTH 網店自動系統"
    assert xau["task"]["lane"] == "xau"
    assert xau["task"]["lane_label"] == "XAU 中控"
    assert buyeros["task"]["lane"] == "buyeros"
    assert buyeros["task"]["lane_label"] == "BuyerOS Core"
    assert buyeros_alias["task"]["lane"] == "buyeros"
    assert buyeros_alias_dash["task"]["lane"] == "buyeros"
    assert xau_alias["task"]["lane"] == "xau"
    assert cloth_alias["task"]["lane"] == "cloth"
    assert service.list_tasks(lane="cloth")["items"][0]["content"]["lane"] == "cloth"
    assert service.list_tasks(lane="xau")["items"][0]["content"]["lane"] == "xau"
    assert service.list_tasks(lane="buyeros")["items"][0]["content"]["lane"] == "buyeros"


def test_project_registry_returns_three_canonical_projects_when_old_alias_projects_exist() -> None:
    memory = MemoryStore()
    memory.save_memory(
        ["buyeros", "projects"],
        "buyeros",
        {"project_id": "buyeros", "name": "old BuyerOS"},
        created_by="test",
    )
    memory.save_memory(
        ["buyeros", "projects"],
        "cloth",
        {"project_id": "cloth", "name": "old CLOTH"},
        created_by="test",
    )
    service = ProjectRegistryService(memory)

    projects = service.list_projects()["items"]
    project_ids = {(item.get("content") or {}).get("project_id") for item in projects}
    names = {(item.get("content") or {}).get("name") for item in projects}

    assert project_ids == {"buyeros", "cloth", "xau"}
    assert names == {"BuyerOS Core", "CLOTH 網店自動系統", "XAU 中控"}


def test_three_system_api_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    report = client.post("/reports/create", json={"period": "daily", "date": "2026-05-22"}, headers=headers)
    history = client.get("/reports/history", headers=headers)
    export = client.post("/reports/export", json={"report_id": "daily-2026-05-22"}, headers=headers)
    campaign = client.post(
        "/promo/campaigns",
        json={"name": "XAU May Promo", "offer": "Gold promo", "budget_hkd": 500},
        headers=headers,
    )
    campaign_id = campaign.json()["campaign"]["campaign_id"]
    event = client.post(
        "/promo/events",
        json={"campaign_id": campaign_id, "event_type": "conversion", "value_hkd": 99},
        headers=headers,
    )
    metrics = client.get(f"/promo/metrics?campaign_id={campaign_id}", headers=headers)
    task = client.post("/tasks", json={"title": "AI team task", "lane": "buyeros"}, headers=headers)
    task_id = task.json()["task"]["task_id"]
    task_run = client.post(f"/tasks/{task_id}/run", json={"result": "completed", "provider": "openai"}, headers=headers)
    tasks = client.get("/tasks", headers=headers)
    projects = client.get("/projects", headers=headers)

    for response in [report, history, export, campaign, event, metrics, task, task_run, tasks, projects]:
        assert response.status_code == 200
        assert response.json()["ok"] is True

    assert task.json()["task"]["lane"] == "buyeros"
    assert task.json()["task"]["lane_label"] == "BuyerOS Core"
    project_ids = {(item.get("content") or {}).get("project_id") for item in projects.json()["items"]}
    assert project_ids == {"buyeros", "cloth", "xau"}


def test_three_system_api_validates_payload(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    response = client.post("/promo/campaigns", json={"name": "", "offer": ""}, headers=headers)

    assert response.status_code == 422


def test_three_systems_smoke_script_exists_and_is_executable() -> None:
    path = REPO_ROOT / "infra/smoke_four_systems.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)


def test_primary_smoke_script_runs_three_systems_by_default() -> None:
    with open(REPO_ROOT / "infra/smoke_api.sh", "r", encoding="utf-8") as fh:
        script = fh.read()

    assert "smoke_four_systems.sh" in script
    assert "BUYEROS_SKIP_FOUR_SYSTEMS_SMOKE" in script


def test_legacy_three_systems_smoke_script_wraps_three_systems() -> None:
    path = REPO_ROOT / "infra/smoke_three_systems.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "smoke_four_systems.sh" in script


def test_deploy_and_smoke_script_exists_and_uses_safe_steps() -> None:
    path = REPO_ROOT / "infra/deploy_and_smoke.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "validate_env.py --env" in script
    assert "deploy_vps.sh" in script
    assert "smoke_api.sh" in script
    assert "BUYEROS_API_KEY" in script


def test_24h_smoke_script_exists_and_runs_primary_smoke_loop() -> None:
    path = REPO_ROOT / "infra/smoke_24h.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "smoke_api.sh" in script
    assert "DURATION_HOURS=\"${3:-24}\"" in script
    assert "INTERVAL_SECONDS=\"${4:-3600}\"" in script
    assert "FAILURES" in script


def test_smoke_full_script_exists() -> None:
    path = REPO_ROOT / "infra/smoke_full.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "smoke_api.sh" in script
    assert "npm run ui:smoke" in script
    assert "BUYEROS_API_KEY" in script


def test_run_ops_drill_syncs_summaries_even_when_failover_fails() -> None:
    path = REPO_ROOT / "infra/run_ops_drill.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "FAILOVER_STATUS=0" in script
    assert "|| FAILOVER_STATUS=$?" in script
    assert "rsync -az \"$SUMMARY_DIR/\"" in script
    assert "Summaries were synced" in script


def test_staging_rollback_drill_script_exists_and_never_targets_primary_rollback() -> None:
    path = REPO_ROOT / "infra/run_staging_rollback_drill.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "backup_vps.sh\" \"$STAGING_SSH\"" in script
    assert "rollback_vps.sh\" \"$STAGING_SSH\"" in script
    assert "rollback_vps.sh\" \"$PRIMARY_SSH\"" not in script
    assert "smoke_api.sh\" \"$STAGING_URL\"" in script


def test_rollback_vps_supports_release_layout_current_symlink() -> None:
    path = REPO_ROOT / "infra/rollback_vps.sh"

    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    assert "$REMOTE_DIR/current/docker-compose.yml" in script
    assert "COMPOSE_DIR='$REMOTE_DIR/current'" in script
    assert "No docker-compose.yml found" in script
