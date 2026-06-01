"""OCR service for receipt and document scanning using OCR.Space API."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


class OCRService:
    """Service for OCR operations using OCR.Space API."""

    def __init__(self) -> None:
        self._api_key = os.getenv("OCR_SPACE_API_KEY", "")
        self._api_url = os.getenv("OCR_API_URL", "https://api.ocr.space/parse/image")

    def configured(self) -> bool:
        """Check if OCR service is configured with an API key."""
        return bool(self._api_key)

    def extract_text(
        self, image_url: str = "", language: str = "auto", **kwargs: Any
    ) -> Dict[str, Any]:
        """Extract text from an image URL."""
        import requests

        if not self._api_key or not image_url:
            return {
                "ok": "false",
                "provider": "local_fallback",
                "text": "OCR service not configured or no image URL provided",
            }

        try:
            response = requests.post(
                self._api_url,
                data={"apikey": self._api_key, "language": language, "url": image_url},
                headers={"apikey": self._api_key},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            parsed_results = data.get("ParsedResults", [])
            if parsed_results:
                text_parts = [r.get("ParsedText", "") for r in parsed_results if r.get("ParsedText")]
                if text_parts:
                    text = "\n".join(text_parts)
                    return {"ok": "true", "provider": "ocr_space", "text": text}
                return {"ok": "true", "provider": "ocr_space", "text": "未提取到文字"}
            return {"ok": "true", "provider": "ocr_space", "text": "未提取到文字"}
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                raise requests.HTTPError("429 Too Many Requests")
            raise
        except requests.RequestException as e:
            return {"ok": "false", "provider": "ocr_space", "text": str(e)}

    def extract_receipt_data(self, image_url: str = "") -> Dict[str, Any]:
        """Extract receipt data from an image URL."""
        result = self.extract_text(image_url)
        return {"amount": None, "date": None, "merchant": None, "text": result.get("text", "")}
