"""OpenRouter adapter with graceful fallback when no API key is present."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

from ..provider_registry import BaseProviderAdapter


class OpenRouterProviderAdapter(BaseProviderAdapter):
    name = "openrouter"

    def run(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini")
        if not api_key:
            return {
                "provider": self.name,
                "ok": False,
                "reply": "[openrouter] OPENROUTER_API_KEY is not configured; stored task context only.",
            }
        context_text = "\n".join(str((item.get("content") or {}).get("summary") or item.get("content")) for item in (context or [])[:5])
        messages = [
            {"role": "system", "content": "You are a BuyerOS provider. Use the supplied shared context and answer concisely."},
            {"role": "user", "content": f"Shared context:\n{context_text}\n\nTask:\n{prompt}"},
        ]
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return {"provider": self.name, "ok": True, "reply": reply, "model": model}
