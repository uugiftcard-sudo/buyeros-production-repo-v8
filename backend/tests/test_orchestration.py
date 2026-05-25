from __future__ import annotations

from fastapi.testclient import TestClient

from app.workflows.main import create_app


def _state_payload(trace_id: str = "trc_555") -> dict[str, str]:
    return {
        "agent_id": "agent_alpha",
        "trace_id": trace_id,
        "status": "EXECUTING",
        "node": "RUNPOD_WORKER",
        "level": "INFO",
        "message": "Downloading model weights inside RunPod container",
    }


def test_orchestration_state_update_agent_state_and_timeline(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("BUYEROS_API_KEY", raising=False)
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/orchestration/state-update", json=_state_payload())

        assert response.status_code == 200
        assert response.json() == {
            "status": "synchronized",
            "agent_id": "agent_alpha",
            "trace_id": "trc_555",
        }

        state = client.get("/api/v1/orchestration/agent/agent_alpha")
        assert state.status_code == 200
        assert state.json()["current_status"] == "EXECUTING"
        assert state.json()["current_trace_id"] == "trc_555"

        timeline = client.get("/api/v1/orchestration/trace/trc_555/timeline")
        assert timeline.status_code == 200
        body = timeline.json()
        assert body["trace_id"] == "trc_555"
        assert body["logs"][0]["node"] == "RUNPOD_WORKER"
        assert body["logs"][0]["level"] == "INFO"


def test_orchestration_routes_require_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("BUYEROS_API_KEY", "secret")
    with TestClient(create_app()) as client:
        denied = client.post("/api/v1/orchestration/state-update", json=_state_payload())
        assert denied.status_code == 401

        allowed = client.post(
            "/api/v1/orchestration/state-update",
            json=_state_payload(),
            headers={"Authorization": "Bearer secret"},
        )
        assert allowed.status_code == 200


def test_orchestration_websocket_replays_history(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("BUYEROS_API_KEY", raising=False)
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/orchestration/state-update", json=_state_payload("trc_history"))
        assert response.status_code == 200

        with client.websocket_connect("/ws/trace/trc_history") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "HISTORY_ECHO"
            assert message["logs"][0]["message"] == "Downloading model weights inside RunPod container"


def test_orchestration_websocket_receives_live_updates(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("BUYEROS_API_KEY", raising=False)
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws/trace/trc_live") as websocket:
            response = client.post("/api/v1/orchestration/state-update", json=_state_payload("trc_live"))
            assert response.status_code == 200

            message = websocket.receive_json()
            assert message["agent_id"] == "agent_alpha"
            assert message["status"] == "EXECUTING"
            assert message["latest_log"]["node"] == "RUNPOD_WORKER"
