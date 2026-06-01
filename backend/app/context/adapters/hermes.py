"""Hermes orchestration provider adapter."""

from typing import Any, Dict, List, Optional

from ..provider_registry import BaseProviderAdapter


class HermesProviderAdapter(BaseProviderAdapter):
    name = "hermes"
    is_available = False

    def __init__(self, *args, **kwargs) -> None:
        kwargs["enabled"] = False
        super().__init__(*args, **kwargs)

    def run(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "ok": False,
            "status": "not_configured",
            "reply": "[hermes] provider is explicitly unavailable; falling back to the next provider.",
            "error": "provider_not_configured",
        }
