"""Tests for require_api_key security middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.workflows.main import create_app


class TestRequireApiKey:
    def test_key_not_required_when_env_not_set(self) -> None:
        client = TestClient(create_app())
        response = client.post("/context/search", json={"query": "hello"})
        assert response.status_code == 200

    def test_missing_header_returns_401(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret-key-abc")
        client = TestClient(create_app())
        response = client.post("/context/search", json={"query": "hello"})
        assert response.status_code == 401
        assert "Invalid or missing" in response.json()["detail"]

    def test_wrong_key_returns_401(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "correct-key")
        client = TestClient(create_app())
        response = client.post(
            "/context/search",
            json={"query": "hello"},
            headers={"X-Buyeros-Api-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_correct_x_header_passes(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "correct-key")
        client = TestClient(create_app())
        response = client.post(
            "/context/search",
            json={"query": "hello"},
            headers={"X-Buyeros-Api-Key": "correct-key"},
        )
        assert response.status_code == 200

    def test_correct_bearer_token_passes(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "bearer-key-xyz")
        client = TestClient(create_app())
        response = client.post(
            "/context/search",
            json={"query": "hello"},
            headers={"Authorization": "Bearer bearer-key-xyz"},
        )
        assert response.status_code == 200

    def test_bearer_with_extra_spaces_trimmed(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "my-secret")
        client = TestClient(create_app())
        response = client.post(
            "/context/search",
            json={"query": "hello"},
            headers={"Authorization": "Bearer   my-secret   "},
        )
        assert response.status_code == 200

    def test_bearer_case_insensitive(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "mixed-case")
        client = TestClient(create_app())
        response = client.post(
            "/context/search",
            json={"query": "hello"},
            headers={"authorization": "bearer mixed-case"},
        )
        assert response.status_code == 200

    def test_only_bearer_header_used_when_both_present(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "correct")
        client = TestClient(create_app())
        response = client.post(
            "/context/search",
            json={"query": "hello"},
            headers={
                "X-Buyeros-Api-Key": "wrong",
                "Authorization": "Bearer correct",
            },
        )
        assert response.status_code == 200

    def test_public_endpoints_no_auth_required(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "any-key")
        client = TestClient(create_app())
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_protected_endpoints_require_auth_when_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "admin-secret")
        client = TestClient(create_app())

        for path in ["/providers", "/audit/search", "/context/session/test"]:
            response = client.get(path)
            assert response.status_code == 401, f"{path} should return 401"
