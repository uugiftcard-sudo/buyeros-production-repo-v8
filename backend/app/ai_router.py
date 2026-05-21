"""AI model router backed by OpenRouter with graceful fallback."""

from __future__ import annotations

import os
from typing import Dict

import requests


class AIModelRouter:
    """Route prompts to role-specific models via OpenRouter."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.models: Dict[str, str] = {
            "supervisor": os.getenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini"),
            "ops": os.getenv("OPENROUTER_MODEL_OPS", "openai/gpt-4o-mini"),
            "finance": os.getenv("OPENROUTER_MODEL_FINANCE", "openai/gpt-4o-mini"),
        }

    def route(self, *, role: str, prompt: str) -> str:
        model = self.models.get(role, self.models["supervisor"])
        if not self.api_key:
            return f"[AI fallback:{role}] {prompt}"
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are BuyerOS {role} assistant. Reply concise Traditional Chinese."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
