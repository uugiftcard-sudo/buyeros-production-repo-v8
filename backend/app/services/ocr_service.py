"""OCR provider integration."""

from __future__ import annotations

import os
from typing import Dict

import requests


class OCRService:
    """Simple OCR wrapper using OCR.Space API when configured."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OCR_SPACE_API_KEY", "")
        self.endpoint = os.getenv("OCR_API_URL", "https://api.ocr.space/parse/image")

    def configured(self) -> bool:
        return bool(self.api_key)

    def extract_text(self, *, image_url: str = "", language: str = "eng") -> Dict[str, str]:
        if not self.configured() or not image_url:
            return {
                "ok": "false",
                "text": "暫未接入 OCR 服務或未提供圖片 URL，無法識別文字。",
                "provider": "local_fallback",
            }
        response = requests.post(
            self.endpoint,
            data={"url": image_url, "language": language, "isOverlayRequired": False},
            headers={"apikey": self.api_key},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        parsed = data.get("ParsedResults") or []
        text = "\n".join((item.get("ParsedText") or "").strip() for item in parsed).strip()
        if not text:
            text = "OCR 已執行，但未提取到文字。"
        return {"ok": "true", "text": text, "provider": "ocr_space"}
