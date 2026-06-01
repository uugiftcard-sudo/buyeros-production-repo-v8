"""OCR.Space integration with a local fallback."""

from __future__ import annotations

import os
from typing import Any

import requests


class OCRService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OCR_SPACE_API_KEY", "").strip()
        self.api_url = os.getenv("OCR_API_URL", "https://api.ocr.space/parse/image").strip()

    def configured(self) -> bool:
        return bool(self.api_key)

    def extract_text(self, *, image_url: str, language: str = "eng") -> dict[str, Any]:
        if not self.configured() or not image_url:
            return {
                "ok": "false",
                "provider": "local_fallback",
                "text": "OCR 未配置或缺少圖片 URL，請稍後再試。",
            }

        response = requests.post(
            self.api_url,
            headers={"apikey": self.api_key},
            data={
                "url": image_url,
                "language": language,
                "isOverlayRequired": "false",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("ParsedResults") or []
        text = "\n".join(str(item.get("ParsedText") or "") for item in results).strip()
        if not text:
            text = "未提取到文字。"
        return {"ok": "true", "provider": "ocr_space", "text": text, "raw": data}
