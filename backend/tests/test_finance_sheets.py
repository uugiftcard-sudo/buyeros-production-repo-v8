"""Tests for FinanceSheetsService (Google Sheets API integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.finance_sheets import FinanceSheetsService


class TestFinanceSheetsService:
    def test_configured_true_when_spreadsheet_id_and_service_account_set(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "abc123")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email":"x@x.iam.gserviceaccount.com","private_key":"-----BEGIN RSA PRIVATE KEY-----\\nMIIE\\n-----END RSA PRIVATE KEY-----\\n"}')
        service = FinanceSheetsService()
        assert service.configured() is True

    def test_configured_true_when_spreadsheet_id_and_api_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "abc123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIza")
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
        service = FinanceSheetsService()
        assert service.configured() is True

    def test_configured_false_when_spreadsheet_id_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIza")
        service = FinanceSheetsService()
        assert service.configured() is False

    def test_configured_false_when_no_auth_set(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "abc123")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "")
        service = FinanceSheetsService()
        assert service.configured() is False

    def test_get_profit_summary_success(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIzaSyD")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valueRanges": [
                {
                    "values": [
                        ["月份", "HKD金額", "退款筆數"],
                        [202401, 15230.5, 3],
                    ]
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            service = FinanceSheetsService()
            result = service.get_profit_summary()
            assert result["ok"] is True
            assert result["source"] == "google_sheets"
            assert result["data"]["month"] == "202401"
            assert result["data"]["profit_hkd"] == 15230.5
            assert result["data"]["refund_count"] == 3

    def test_get_profit_summary_empty_rows_returns_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIzaSyD")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valueRanges": [{"values": [["月份", "HKD金額", "退款筆數"]]}]}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            service = FinanceSheetsService()
            result = service.get_profit_summary()
            assert result["ok"] is True
            assert result["source"] == "google_sheets_error"
            assert result["data"]["profit_hkd"] == 0
            assert result["data"]["refund_count"] == 0

    def test_get_profit_summary_api_error_returns_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIzaSyD")

        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

        with patch("requests.get", return_value=mock_response):
            service = FinanceSheetsService()
            result = service.get_profit_summary()
            assert result["ok"] is True
            assert result["source"] == "google_sheets_error"
            assert result["data"]["profit_hkd"] == 0

    def test_get_payout_schedule_success(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIzaSyD")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valueRanges": [
                {
                    "values": [
                        ["下次出糧日", "幣種", "狀態"],
                        [25, "HKD", "pending"],
                    ]
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            service = FinanceSheetsService()
            result = service.get_payout_schedule()
            assert result["ok"] is True
            assert result["source"] == "google_sheets"
            assert result["data"]["next_payout_day"] == 25
            assert result["data"]["currency"] == "HKD"
            assert result["data"]["status"] == "pending"

    def test_get_payout_schedule_empty_rows_returns_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIzaSyD")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valueRanges": [{"values": [["下次出糧日", "幣種", "狀態"]]}]}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            service = FinanceSheetsService()
            result = service.get_payout_schedule()
            assert result["ok"] is True
            assert result["source"] == "google_sheets_error"
            assert result["data"]["next_payout_day"] == 5
            assert result["data"]["currency"] == "HKD"

    def test_get_payout_schedule_api_error_returns_fallback(self, monkeypatch) -> None:
        monkeypatch.setenv("GOOGLE_SHEETS_ID", "sheet123")
        monkeypatch.setenv("GOOGLE_SHEETS_API_KEY", "AIzaSyD")

        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with patch("requests.get", return_value=mock_response):
            service = FinanceSheetsService()
            result = service.get_payout_schedule()
            assert result["ok"] is True
            assert result["source"] == "google_sheets_error"
            assert result["data"]["next_payout_day"] == 5
