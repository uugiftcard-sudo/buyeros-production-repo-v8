"""OCR tool with optional remote OCR provider integration."""

from typing import Dict

from ..services.ocr_service import OCRService


def extract_text(args: Dict[str, str]) -> str:
    """Extract text from image URL when OCR provider is configured."""
    service = OCRService()
    result = service.extract_text(image_url=args.get("image_url", ""), language=args.get("language", "eng"))
    return result.get("text", "OCR 執行失敗。")
