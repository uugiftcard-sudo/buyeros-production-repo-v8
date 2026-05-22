"""Tests for payment gateway: PaymentGatewayClient, StripeAdapter, PayPalAdapter, CustomRestAdapter, PaymentGatewayMulti."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.payment_gateway import PaymentGatewayClient
from app.services.payment_gateway_multi import PaymentGatewayMulti
from app.services.adapters.stripe_adapter import StripeAdapter
from app.services.adapters.paypal_adapter import PayPalAdapter
from app.services.adapters.custom_adapter import CustomRestAdapter


class TestPaymentGatewayClient:
    def test_configured_returns_true_when_url_and_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "https://gateway.example.com")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "sk_test_123")
        client = PaymentGatewayClient()
        assert client.configured() is True

    def test_configured_returns_false_when_url_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "sk_test_123")
        client = PaymentGatewayClient()
        assert client.configured() is False

    def test_configured_returns_false_when_key_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "https://gateway.example.com")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "")
        client = PaymentGatewayClient()
        assert client.configured() is False

    def test_refund_not_configured_returns_local_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "")
        client = PaymentGatewayClient()
        result = client.refund("TXN123")
        assert result["ok"] is False
        assert result["provider"] == "local_fallback"
        assert result["status"] == "not_configured"

    def test_refund_success_returns_normalised_response(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "https://gateway.example.com")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "sk_test_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "submitted", "message": "Refund OK"}'
        mock_response.json.return_value = {"status": "submitted", "message": "Refund OK"}

        with patch("requests.post", return_value=mock_response) as mock_post:
            client = PaymentGatewayClient()
            result = client.refund("TXN456", amount=99.5, reason="Customer request")
            assert result["ok"] is True
            assert result["provider"] == "remote_gateway"
            assert result["status"] == "submitted"
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer sk_test_123"
            assert call_kwargs["json"]["transaction_id"] == "TXN456"
            assert call_kwargs["json"]["amount"] == 99.5
            assert call_kwargs["json"]["reason"] == "Customer request"

    def test_refund_http_error_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "https://gateway.example.com")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "sk_test_123")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("422 Unprocessable Entity")

        with patch("requests.post", return_value=mock_response):
            client = PaymentGatewayClient()
            with pytest.raises(requests.HTTPError):
                client.refund("TXN789")


class TestStripeAdapter:
    def test_configured_true_when_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "sk_test_abc")
        adapter = StripeAdapter()
        assert adapter.configured() is True

    def test_configured_false_when_key_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "")
        adapter = StripeAdapter()
        assert adapter.configured() is False

    def test_refund_success(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "sk_test_abc")
        monkeypatch.setenv("STRIPE_API_VERSION", "2024-04-10")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "re_123",
            "status": "succeeded",
            "amount": 5000,
            "currency": "hkd",
        }

        with patch("requests.post", return_value=mock_response):
            adapter = StripeAdapter()
            result = adapter.refund("ch_abc", amount=50.0, reason="No stock")
            assert result["provider"] == "stripe"
            assert result["status"] == "succeeded"
            assert result["refund_id"] == "re_123"
            assert result["amount"] == 50.0  # converted from cents

    def test_refund_error_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "sk_test_abc")
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("Charge not found")

        with patch("requests.post", return_value=mock_response):
            adapter = StripeAdapter()
            with pytest.raises(requests.HTTPError):
                adapter.refund("ch_unknown")


class TestPayPalAdapter:
    def test_configured_true_when_credentials_set(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "client_id")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client_secret")
        adapter = PayPalAdapter()
        assert adapter.configured() is True

    def test_configured_false_when_client_id_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client_secret")
        adapter = PayPalAdapter()
        assert adapter.configured() is False

    def test_refund_success(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "client_id")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client_secret")
        monkeypatch.setenv("PAYPAL_MODE", "sandbox")

        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {"access_token": "access_token_xyz"}
        mock_auth_response.raise_for_status = MagicMock()

        mock_refund_response = MagicMock()
        mock_refund_response.status_code = 201
        mock_refund_response.json.return_value = {
            "id": "refund_456",
            "status": "COMPLETED",
            "amount": {"value": "99.00", "currency_code": "HKD"},
        }
        mock_refund_response.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[mock_auth_response, mock_refund_response]):
            adapter = PayPalAdapter()
            result = adapter.refund("capture_xyz", amount=99.0, reason="Defective")
            assert result["provider"] == "paypal"
            assert result["status"] == "COMPLETED"
            assert result["refund_id"] == "refund_456"

    def test_refund_auth_error_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "client_id")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client_secret")
        monkeypatch.setenv("PAYPAL_MODE", "sandbox")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

        with patch("requests.post", return_value=mock_response):
            adapter = PayPalAdapter()
            with pytest.raises(requests.HTTPError):
                adapter.refund("capture_xyz")


class TestCustomRestAdapter:
    def test_configured_true_when_url_and_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "https://custom.example.com")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "key_abc")
        adapter = CustomRestAdapter()
        assert adapter.configured() is True

    def test_configured_false_when_base_url_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "key_abc")
        adapter = CustomRestAdapter()
        assert adapter.configured() is False

    def test_refund_success(self, monkeypatch) -> None:
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "https://custom.example.com")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "key_abc")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"refund_id": "ref_789", "status": "submitted"}'
        mock_response.json.return_value = {"refund_id": "ref_789", "status": "submitted"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            adapter = CustomRestAdapter()
            result = adapter.refund("TXN999", amount=25.0)
            assert result["provider"] == "custom_rest"
            assert result["status"] == "submitted"
            assert result["refund_id"] == "ref_789"


class TestPaymentGatewayMulti:
    def test_all_providers_unconfigured_returns_local_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "")
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "")
        gateway = PaymentGatewayMulti()
        result = gateway.refund("TXN000")
        assert result["ok"] is False
        assert result["provider"] == "local_fallback"
        assert result["status"] == "not_configured"

    def test_stripe_configured_used_as_primary(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "sk_test_stripe")
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "re_test",
            "status": "succeeded",
            "amount": 3000,
            "currency": "hkd",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            gateway = PaymentGatewayMulti()
            result = gateway.refund("TXN111", amount=30.0)
            assert result["ok"] is True
            assert result["provider"] == "stripe"

    def test_stripe_fails_paypal_used_as_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "sk_test_stripe")
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "client_id")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client_secret")
        monkeypatch.setenv("PAYPAL_MODE", "sandbox")
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "")

        stripe_error = requests.HTTPError("Stripe down")
        stripe_mock = MagicMock()
        stripe_mock.raise_for_status.side_effect = stripe_error

        auth_mock = MagicMock()
        auth_mock.status_code = 200
        auth_mock.json.return_value = {"access_token": "token"}
        auth_mock.raise_for_status = MagicMock()

        refund_mock = MagicMock()
        refund_mock.status_code = 201
        refund_mock.json.return_value = {
            "id": "pp_refund",
            "status": "COMPLETED",
            "amount": {"value": "0.00", "currency_code": "HKD"},
        }
        refund_mock.raise_for_status = MagicMock()

        with patch("requests.post", side_effect=[stripe_mock, auth_mock, refund_mock]):
            gateway = PaymentGatewayMulti()
            result = gateway.refund("TXN222")
            assert result["ok"] is True
            assert result["provider"] == "paypal"

    def test_all_adapters_fail_returns_all_providers_failed(self, monkeypatch) -> None:
        monkeypatch.setenv("STRIPE_API_KEY", "sk_test_stripe")
        monkeypatch.setenv("PAYPAL_CLIENT_ID", "client_id")
        monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client_secret")
        monkeypatch.setenv("PAYPAL_MODE", "sandbox")
        monkeypatch.setenv("PAYMENT_GATEWAY_BASE_URL", "")
        monkeypatch.setenv("PAYMENT_GATEWAY_API_KEY", "")

        stripe_error = requests.HTTPError("Stripe down")
        stripe_mock = MagicMock()
        stripe_mock.raise_for_status.side_effect = stripe_error

        auth_error = requests.HTTPError("PayPal auth down")
        auth_mock = MagicMock()
        auth_mock.raise_for_status.side_effect = auth_error

        with patch("requests.post", side_effect=[stripe_mock, auth_mock]):
            gateway = PaymentGatewayMulti()
            result = gateway.refund("TXN333")
            assert result["ok"] is False
            assert result["provider"] == "none"
            assert result["status"] == "all_providers_failed"
