from fastapi.testclient import TestClient

from app.workflows.main import create_app


def test_context_api_write_search_and_agent_run() -> None:
    client = TestClient(create_app())

    write_response = client.post(
        "/context/write",
        json={
            "source_provider": "claude",
            "session_id": "api-session",
            "task_id": "api-task",
            "content": {"text": "Cursor can reuse this context for transaction 991"},
            "summary": "Transaction 991 context",
        },
    )
    assert write_response.status_code == 200
    assert write_response.json()["ok"] is True

    search_response = client.post(
        "/context/search",
        json={"query": "991", "session_id": "api-session"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["items"]

    run_response = client.post(
        "/agents/run",
        json={"prompt": "fix code using transaction 991 context", "user_id": "api", "session_id": "api-session"},
    )
    assert run_response.status_code == 200
    assert run_response.json()["ok"] is True


def test_context_api_requires_key_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())

    denied = client.post("/context/search", json={"query": "991"})
    assert denied.status_code == 401

    allowed = client.post(
        "/context/search",
        json={"query": "991"},
        headers={"X-Buyeros-Api-Key": "secret"},
    )
    assert allowed.status_code == 200


def test_providers_and_audit_search_require_key_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    client = TestClient(create_app())

    denied = client.get("/providers")
    assert denied.status_code == 401

    providers = client.get("/providers", headers={"Authorization": "Bearer secret"})
    assert providers.status_code == 200
    assert providers.json()["providers"]

    client.post(
        "/context/write",
        json={"source_provider": "claude", "content": {"text": "audit me"}},
        headers={"Authorization": "Bearer secret"},
    )
    audit = client.get("/audit/search", headers={"Authorization": "Bearer secret"})
    assert audit.status_code == 200
    assert audit.json()["items"]


def test_ready_endpoint_reports_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "memory" in body
    assert "providers" in body


def test_system_capabilities_requires_key_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    client = TestClient(create_app())

    denied = client.get("/system/capabilities")
    assert denied.status_code == 401

    allowed = client.get("/system/capabilities", headers={"Authorization": "Bearer secret"})
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["ok"] is True
    assert "supervisor" in body["agents"]
    assert "refund" in body["tools"]
    assert isinstance(body["providers"], list)
    assert "missing_env" in body["gaps"]
