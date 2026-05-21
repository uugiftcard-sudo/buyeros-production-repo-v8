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


def test_telegram_webhook_malformed_json_returns_400(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    client = TestClient(create_app())

    response = client.post(
        "/telegram/webhook",
        content=b"not valid json",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": "telegram-secret",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 400


def test_telegram_webhook_no_message_returns_ok_empty(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    client = TestClient(create_app())

    response = client.post(
        "/telegram/webhook",
        json={"update_id": 123456789},
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_telegram_webhook_no_text_returns_ok(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    client = TestClient(create_app())

    # Message with no text field
    response = client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 123}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_telegram_webhook_edited_message_handled(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    client = TestClient(create_app())

    response = client.post(
        "/telegram/webhook",
        json={"edited_message": {"chat": {"id": 456}, "text": "edited text"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )
    assert response.status_code == 200

