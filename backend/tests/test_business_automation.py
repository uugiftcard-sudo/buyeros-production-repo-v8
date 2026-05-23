from __future__ import annotations

from fastapi.testclient import TestClient

from app.memory_store import MemoryStore
from app.services.business_automation import BusinessAutomationService
from app.services.ops_status_service import OpsStatusService
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
    assert "ocr_entries" in result["data"]["counts"]
    assert "approvals" in result["data"]["counts"]
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
    close_cycle = client.post(
        "/automation/close-cycle",
        json={
            "ocr_text": "No amount here",
            "expected_total": 100,
            "actual_total": 95,
            "reference": "api-cycle",
            "high_risk": True,
            "retry_error": "timeout",
            "retry_attempt": 1,
        },
        headers=headers,
    )

    for response in [report, ocr, recon, alerts, approval, retry, close_cycle]:
        assert response.status_code == 200
        assert response.json()["ok"] is True
    assert close_cycle.json()["workflow"] == "close_cycle"
    assert close_cycle.json()["status"] == "needs_review"


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


def test_close_cycle_persists_all_operational_records() -> None:
    memory = MemoryStore()
    service = BusinessAutomationService(memory)

    result = service.close_cycle(
        ocr_text="Receipt without amount",
        expected_total=100,
        actual_total=90,
        reference="cycle-1",
        high_risk=True,
        retry_error="provider timeout",
    )

    assert result["ok"] is True
    assert result["workflow"] == "close_cycle"
    assert result["status"] == "needs_review"
    assert memory.search_memory(namespace_prefix=("buyeros", "ocr_entries"), limit=10)
    assert memory.search_memory(namespace_prefix=("buyeros", "reconciliation"), memory_key="cycle-1")
    assert memory.search_memory(namespace_prefix=("buyeros", "alerts"), limit=10)
    assert memory.search_memory(namespace_prefix=("buyeros", "approvals"), limit=10)
    assert memory.search_memory(namespace_prefix=("buyeros", "retries"), limit=10)
    assert memory.search_memory(namespace_prefix=("buyeros", "reports"), limit=10)
    assert memory.search_memory(namespace_prefix=("buyeros", "close_cycles"), limit=10)


def test_close_cycle_uses_order_total_and_ocr_image_text() -> None:
    class FakeOrders:
        def get_order(self, order_id: str) -> dict:
            return {"order_id": order_id, "total_hkd": "100.00", "currency": "HKD", "status": "paid"}

    class FakeOcr:
        def extract_text(self, *, image_url: str = "", language: str = "eng") -> dict:
            return {"ok": "true", "text": "Receipt total HKD 88.00", "provider": "ocr_space"}

    memory = MemoryStore()
    service = BusinessAutomationService(memory, orders_service=FakeOrders(), ocr_service=FakeOcr())

    result = service.close_cycle(
        ocr_text="fallback text",
        expected_total=None,
        actual_total=None,
        order_id="991",
        image_url="https://example.com/receipt.jpg",
        reference="cycle-real-991",
    )

    assert result["ok"] is True
    assert result["status"] == "needs_review"
    assert result["data"]["expected_total_source"] == "order"
    assert result["data"]["actual_total_source"] == "ocr"
    assert result["data"]["reconciliation"]["data"]["expected_total"] == 100
    assert result["data"]["reconciliation"]["data"]["actual_total"] == 88
    assert memory.search_memory(namespace_prefix=("buyeros", "orders"), memory_key="991")


def test_close_cycle_missing_order_or_ocr_amount_creates_approval() -> None:
    class FakeOrders:
        def get_order(self, order_id: str) -> dict:
            return {"order_id": order_id, "error": "not found"}

    class FakeOcr:
        def extract_text(self, *, image_url: str = "", language: str = "eng") -> dict:
            return {"ok": "true", "text": "Receipt without amount", "provider": "ocr_space"}

    memory = MemoryStore()
    service = BusinessAutomationService(memory, orders_service=FakeOrders(), ocr_service=FakeOcr())

    result = service.close_cycle(
        ocr_text="fallback text",
        expected_total=None,
        actual_total=None,
        order_id="missing",
        image_url="https://example.com/blank.jpg",
        reference="cycle-review",
    )

    assert result["status"] == "needs_review"
    assert result["data"]["approval"] is not None
    assert result["data"]["review_reasons"]


def test_ops_status_reads_latest_summaries(tmp_path) -> None:
    (tmp_path / "backup-latest.json").write_text(
        '{"ok":true,"action":"backup","target":"host","started_at":"2026-05-23T00:00:00Z","ended_at":"2026-05-23T00:00:01Z","duration_seconds":1,"notes":"Backup created","archive_path":"host:/backup.tgz"}',
        encoding="utf-8",
    )

    status = OpsStatusService(str(tmp_path)).status()

    assert status["ok"] is True
    assert status["summaries"]["backup"]["ok"] is True
    assert status["summaries"]["rollback"]["status"] == "尚無執行紀錄"
