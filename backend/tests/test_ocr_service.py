"""Tests for OCRService (OCR.Space API integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.ocr_service import OCRService


class TestOCRService:
    def test_configured_true_when_api_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "helloworld")
        service = OCRService()
        assert service.configured() is True

    def test_configured_false_when_api_key_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "")
        service = OCRService()
        assert service.configured() is False

    def test_extract_text_returns_fallback_when_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "")
        monkeypatch.setenv("OCR_API_URL", "https://api.ocr.space/parse/image")
        service = OCRService()
        result = service.extract_text(image_url="https://example.com/receipt.jpg")
        assert result["ok"] == "false"
        assert result["provider"] == "local_fallback"
        # Fallback message is returned when key is missing
        assert result["text"]

    def test_extract_text_returns_fallback_when_no_url(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "helloworld")
        service = OCRService()
        result = service.extract_text(image_url="")
        assert result["ok"] == "false"
        assert result["provider"] == "local_fallback"

    def test_extract_text_success(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "helloworld")
        monkeypatch.setenv("OCR_API_URL", "https://api.ocr.space/parse/image")
        service = OCRService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ParsedResults": [
                {"ParsedText": "Receipt Total: HKD 99.00\nDate: 2024-01-15"},
                {"ParsedText": ""},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = service.extract_text(image_url="https://example.com/receipt.jpg", language="eng")
            assert result["ok"] == "true"
            assert result["provider"] == "ocr_space"
            assert "Receipt Total: HKD 99.00" in result["text"]
            assert "Date: 2024-01-15" in result["text"]

            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"]["apikey"] == "helloworld"

    def test_extract_text_empty_result_returns_fallback_message(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "helloworld")
        service = OCRService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ParsedResults": []}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = service.extract_text(image_url="https://example.com/blank.jpg")
            assert result["ok"] == "true"
            assert "未提取到文字" in result["text"]

    def test_extract_text_rate_limit_error(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "helloworld")
        service = OCRService()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(requests.HTTPError) as exc_info:
                service.extract_text(image_url="https://example.com/receipt.jpg")
            assert "429" in str(exc_info.value)

    def test_extract_text_server_error(self, monkeypatch) -> None:
        monkeypatch.setenv("OCR_SPACE_API_KEY", "helloworld")
        service = OCRService()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                service.extract_text(image_url="https://example.com/receipt.jpg")
