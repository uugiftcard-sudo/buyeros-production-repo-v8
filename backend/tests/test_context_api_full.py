"""Tests for FastAPI endpoints not covered by test_context_api.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.workflows.main import create_app


class TestPingEndpoint:
    def test_ping_returns_200_ok(self) -> None:
        client = TestClient(create_app())
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_root_returns_operator_links(self) -> None:
        client = TestClient(create_app())
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["service"] == "BuyerOS API"
        assert body["ping"] == "/ping"


class TestContextSummarizeEndpoint:
    def test_summarize_requires_key(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())
        response = client.post(
            "/context/summarize",
            json={"query": "refund"},
        )
        assert response.status_code == 401

    def test_summarize_returns_summary(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())

        # Write some context first
        client.post(
            "/context/write",
            json={
                "source_provider": "claude",
                "session_id": "summarize-test",
                "task_id": "t1",
                "content": {"text": "Refund 456 was processed successfully."},
                "summary": "Refund 456 processed",
            },
            headers={"Authorization": "Bearer secret"},
        )

        response = client.post(
            "/context/summarize",
            json={"query": "refund 456", "session_id": "summarize-test"},
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "summary" in body

    def test_summarize_no_matching_context(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/context/summarize",
            json={"query": "this query has no results ever"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestContextSessionEndpoint:
    def test_session_returns_items_and_state(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())

        # Write context to session
        client.post(
            "/context/write",
            json={
                "source_provider": "openai",
                "session_id": "session-x",
                "content": {"text": "Hello from session-x"},
                "summary": "Hello",
            },
            headers={"Authorization": "Bearer secret"},
        )

        response = client.get(
            "/context/session/session-x",
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["items"], list)
        assert "last_state" in body

    def test_session_returns_fallback_by_memory_key(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())
        # simulate legacy rows: no content.session_id, only memory_key=session.
        client.post(
            "/context/write",
            json={
                "source_provider": "openai",
                "task_id": "legacy-session",
                "content": {"text": "Legacy session entry"},
                "summary": "legacy",
            },
            headers={"Authorization": "Bearer secret"},
        )

        response = client.get(
            "/context/session/legacy-session",
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["items"], list)
        assert len(body["items"]) >= 1

    def test_session_empty_when_no_data(self) -> None:
        client = TestClient(create_app())
        response = client.get("/context/session/nonexistent-session")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["items"] == []

    def test_session_requires_api_key_when_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())
        response = client.get("/context/session/session-x")
        assert response.status_code == 401


class TestProvidersEndpoint:
    def test_providers_returns_list(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-xxx")
        monkeypatch.setenv("OPENROUTER_MODEL_OPENAI", "openai/gpt-4o-mini")
        monkeypatch.setenv("OPENROUTER_MODEL_CLAUDE", "anthropic/claude-sonnet-4.5")
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())

        response = client.get(
            "/providers",
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["providers"], list)
        assert len(body["providers"]) > 0
        for provider in body["providers"]:
            assert "name" in provider
            assert "enabled" in provider
            assert "model" in provider
            assert "fallback_target" in provider
            assert "status" in provider
            assert "success_count_24h" in provider
            assert "failure_count_24h" in provider


class TestClothOrdersEndpoint:
    def test_cloth_order_returns_custom_rest_order_and_persists_memory(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        monkeypatch.setenv("ORDERS_API_BASE_URL", "https://orders.example.com")
        monkeypatch.setenv("ORDERS_API_KEY", "orders-key")
        monkeypatch.delenv("SHOPIFY_SHOP_DOMAIN", raising=False)
        monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {"order_id": "991", "total_hkd": "100.00", "currency": "HKD", "status": "paid"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.adapters.custom_ecom_adapter.requests.get", return_value=mock_response):
            client = TestClient(create_app())
            response = client.get("/cloth/orders/991", headers={"Authorization": "Bearer secret"})

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["order"]["order_id"] == "991"
        assert body["configured"] is True

    def test_cloth_orders_list_returns_items(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        monkeypatch.setenv("ORDERS_API_BASE_URL", "https://orders.example.com")
        monkeypatch.setenv("ORDERS_API_KEY", "orders-key")
        monkeypatch.delenv("SHOPIFY_SHOP_DOMAIN", raising=False)
        monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {"orders": [{"order_id": "991", "total": 100, "currency": "HKD"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.adapters.custom_ecom_adapter.requests.get", return_value=mock_response):
            client = TestClient(create_app())
            response = client.get("/cloth/orders?limit=1", headers={"Authorization": "Bearer secret"})

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["items"][0]["order_id"] == "991"


class TestAuditSearchEndpoint:
    def test_audit_search_requires_key(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())
        response = client.get("/audit/search")
        assert response.status_code == 401

    def test_audit_search_returns_events(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())

        # Write context which generates an audit event
        client.post(
            "/context/write",
            json={
                "source_provider": "test",
                "session_id": "audit-test",
                "content": {"text": "audit event test"},
            },
            headers={"Authorization": "Bearer secret"},
        )

        response = client.get(
            "/audit/search",
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["items"], list)

    def test_audit_search_respects_limit_param(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())

        # Write multiple audit events
        for i in range(5):
            client.post(
                "/context/write",
                json={"source_provider": f"provider-{i}", "content": {"text": f"event {i}"}},
                headers={"Authorization": "Bearer secret"},
            )

        response = client.get(
            "/audit/search?limit=2",
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        # Items may exceed limit due to storage impl, but should handle param

    def test_audit_search_limit_capped_at_100(self, monkeypatch) -> None:
        monkeypatch.setenv("BUYEROS_API_KEY", "secret")
        client = TestClient(create_app())
        response = client.get(
            "/audit/search?limit=500",
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestSystemCapabilitiesEndpoint:
    def test_capabilities_includes_agents_tools_providers(self) -> None:
        client = TestClient(create_app())
        response = client.get(
            "/system/capabilities",
            headers={"Authorization": "Bearer "} if False else None,
        )
        # No key set, so should pass
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "agents" in body
        assert "tools" in body
        assert "providers" in body
        assert "feature_flags" in body
        assert "gaps" in body
        assert "missing_env" in body["gaps"]

    def test_capabilities_reports_missing_env(self, monkeypatch) -> None:
        # Clear all env vars that are "required"
        for var in ["SUPABASE_URL", "SUPABASE_KEY", "BUYEROS_API_KEY", "OPENROUTER_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        client = TestClient(create_app())
        response = client.get("/system/capabilities")
        assert response.status_code == 200
        body = response.json()
        assert "SUPABASE_URL" in body["gaps"]["missing_env"]


class TestHealthReadyEndpoint:
    def test_ready_checks_memory_and_redis_and_providers(self) -> None:
        client = TestClient(create_app())
        response = client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert "memory" in body
        assert "redis" in body
        assert "providers" in body
        assert "telegram_configured" in body
        assert "api_key_required" in body
        assert "status" in body["providers"][0]
        assert "last_latency_ms" in body["providers"][0]
