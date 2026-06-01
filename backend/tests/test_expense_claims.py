from __future__ import annotations

from fastapi.testclient import TestClient

from app.workflows.main import create_app


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    monkeypatch.setenv("EXPENSE_DB_PATH", str(tmp_path / "expenses.db"))
    return TestClient(create_app())


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer secret"}


def _claim_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "buyer_name": "陳大文",
        "amount": 128.5,
        "currency": "HKD",
        "category": "travel",
        "description": "廣州採購交通費",
        "receipt_url": "https://example.com/receipt.jpg",
    }
    payload.update(overrides)
    return payload


def test_expense_claim_lifecycle_and_filters(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    create_response = client.post("/expenses", json=_claim_payload(), headers=_headers())
    assert create_response.status_code == 200
    created = create_response.json()["claim"]
    assert create_response.json()["ok"] is True
    assert created["buyer_name"] == "陳大文"
    assert created["status"] == "pending"

    list_response = client.get("/expenses?status=pending&buyer_name=大文", headers=_headers())
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["count"] == 1
    assert listed["claims"][0]["id"] == created["id"]

    get_response = client.get(f"/expenses/{created['id']}", headers=_headers())
    assert get_response.status_code == 200
    assert get_response.json()["claim"]["amount"] == 128.5

    approve_response = client.patch(
        f"/expenses/{created['id']}/status",
        json={"status": "approved", "reviewer": "Ruby", "reviewer_note": "OK"},
        headers=_headers(),
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()["claim"]
    assert approved["status"] == "approved"
    assert approved["reviewer"] == "Ruby"
    assert approved["reviewer_note"] == "OK"

    csv_response = client.get("/expenses/export/csv?status=approved", headers=_headers())
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "陳大文" in csv_response.text
    assert "approved" in csv_response.text


def test_expense_claim_validation_errors(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)

    invalid_amount = client.post("/expenses", json=_claim_payload(amount="abc"), headers=_headers())
    assert invalid_amount.status_code == 422

    negative_amount = client.post("/expenses", json=_claim_payload(amount=-1), headers=_headers())
    assert negative_amount.status_code == 422
    assert "amount must be positive" in negative_amount.json()["detail"]

    invalid_category = client.post("/expenses", json=_claim_payload(category="invalid"), headers=_headers())
    assert invalid_category.status_code == 422
    assert "invalid category" in invalid_category.json()["detail"]

    invalid_filter = client.get("/expenses?status=paid", headers=_headers())
    assert invalid_filter.status_code == 422

    missing = client.patch(
        "/expenses/missing/status",
        json={"status": "approved", "reviewer": "Ruby"},
        headers=_headers(),
    )
    assert missing.status_code == 404

    invalid_status = client.patch(
        "/expenses/missing/status",
        json={"status": "pending", "reviewer": "Ruby"},
        headers=_headers(),
    )
    assert invalid_status.status_code == 422

