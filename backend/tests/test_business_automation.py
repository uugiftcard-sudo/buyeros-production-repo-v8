from __future__ import annotations

from fastapi.testclient import TestClient

from app.memory_store import MemoryStore
from app.services.business_automation import BusinessAutomationService
from app.workflows.main import create_app


def test_daily_report_counts_memory_records() -> None:
    memory = MemoryStore()
    memory.save_memory(["buyeros", "refunds"], "991", {"result": "done"}, created_by="test")
    memory.save_memory(["buyeros", "orders"], "ORD001", {"total": 100}, created_by="test")
    service = BusinessAutomationService(memory)

    result = service.create_daily_report(date="2026-05-22")

    assert result["ok"] is True
    assert result["workflow"] == "daily_report"
    assert result["data"]["counts"]["refunds"] == 1
    assert memory.search_memory(namespace_prefix=("buyeros", "reports"), memory_key="2026-05-22")


def test_ocr_posting_extracts_amount_or_requires_review() -> None:
    memory = MemoryStore()
    service = BusinessAutomationService(memory)

    posted = service.post_ocr_entry(text="Receipt HKD 128.50", entry_id="ocr-1")
    review = service.post_ocr_entry(text="No amount here", entry_id="ocr-2")

    assert posted["status"] == "posted"
    assert posted["data"]["amount_hkd"] == 128.5
    assert review["status"] == "needs_review"


def test_reconcile_creates_alert_on_mismatch() -> None:
    memory = MemoryStore()
    service = BusinessAutomationService(memory)

    result = service.reconcile_entries(expected_total=100, actual_total=95, reference="batch-1")

    assert result["status"] == "mismatch"
    assert memory.search_memory(namespace_prefix=("buyeros", "alerts"), memory_key="batch-1")


def test_alert_approval_and_retry_workflows_persist_state() -> None:
    memory = MemoryStore()
    service = BusinessAutomationService(memory)

    alerts = service.generate_alerts(items=[{"id": "a1", "amount": 200}], threshold=100)
    approval = service.request_approval(task_id="task-1", reason="high refund")
    retry = service.record_retry(task_id="task-2", error="timeout", attempt=1)

    assert len(alerts["data"]["alerts"]) == 1
    assert approval["status"] == "pending"
    assert retry["status"] == "retry_scheduled"
    assert memory.search_memory(namespace_prefix=("buyeros", "approvals"), memory_key="task-1")
    assert memory.search_memory(namespace_prefix=("buyeros", "retries"), memory_key="task-2")


def test_automation_api_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    report = client.post("/automation/daily-report", json={"date": "2026-05-22"}, headers=headers)
    ocr = client.post("/automation/ocr-posting", json={"text": "HKD 88", "entry_id": "ocr-api"}, headers=headers)
    recon = client.post(
        "/automation/reconcile",
        json={"expected_total": 100, "actual_total": 90, "reference": "api-recon"},
        headers=headers,
    )
    alerts = client.post("/automation/alerts", json={"items": [{"id": "x", "amount": 9}], "threshold": 1}, headers=headers)
    approval = client.post("/automation/approval", json={"task_id": "ap-1", "reason": "check"}, headers=headers)
    retry = client.post("/automation/retry", json={"task_id": "rt-1", "error": "timeout", "attempt": 2}, headers=headers)

    for response in [report, ocr, recon, alerts, approval, retry]:
        assert response.status_code == 200
        assert response.json()["ok"] is True


def test_automation_api_rejects_invalid_numeric_payload(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer secret"}

    response = client.post(
        "/automation/reconcile",
        json={"expected_total": "bad", "actual_total": 90, "reference": "api-recon"},
        headers=headers,
    )

    assert response.status_code == 422
