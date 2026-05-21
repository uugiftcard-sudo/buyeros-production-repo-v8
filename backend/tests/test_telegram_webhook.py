from fastapi.testclient import TestClient

from app.workflows.main import create_app


def test_telegram_webhook_secret_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    client = TestClient(create_app())

    payload = {"message": {"chat": {"id": 123}, "text": "退款 991"}}

    denied = client.post("/telegram/webhook", json=payload)
    assert denied.status_code == 401

    allowed = client.post(
        "/telegram/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True

