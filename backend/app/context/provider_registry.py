"""Provider registry and thin provider adapters for shared context."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import requests

from .context_hub import ContextHub

logger = logging.getLogger(__name__)


class BaseProviderAdapter:
    """Minimal provider interface used by BuyerOS v1."""

    name = "base"
    default_openrouter_model = "openai/gpt-4o-mini"

    def __init__(self, *, context_hub: ContextHub, enabled: bool = True, model_env: Optional[str] = None) -> None:
        self.context_hub = context_hub
        self.enabled = enabled
        self.model_env = model_env

    def run(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "provider": self.name,
                "ok": False,
                "reply": f"{self.name} provider is not configured yet.",
            }
        api_result = self._run_via_openrouter(prompt, context=context)
        if api_result:
            return api_result
        context_count = len(context or [])
        return {
            "provider": self.name,
            "ok": True,
            "reply": f"[{self.name}] no provider key configured; stored task with {context_count} context item(s): {prompt}",
        }

    def _run_via_openrouter(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return None
        model = os.getenv(self.model_env or f"OPENROUTER_MODEL_{self.name.upper()}", self.default_openrouter_model)
        context_text = "\n".join(
            str((item.get("content") or {}).get("summary") or (item.get("content") or {}).get("content") or item.get("content"))
            for item in (context or [])[:8]
        )
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"You are the {self.name} provider inside BuyerOS. "
                                "Use shared context, answer concisely, and do not invent tool results."
                            ),
                        },
                        {"role": "user", "content": f"Shared context:\n{context_text}\n\nTask:\n{prompt}"},
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            return {"provider": self.name, "ok": True, "reply": reply, "model": model, "via": "openrouter"}
        except Exception as exc:
            logger.error("%s OpenRouter call failed: %s", self.name, exc)
            return {
                "provider": self.name,
                "ok": False,
                "reply": f"[{self.name}] OpenRouter call failed; stored task context only.",
                "error": str(exc),
                "model": model,
                "via": "openrouter",
            }

    def write_context(
        self,
        result: Dict[str, Any],
        *,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.context_hub.write_context(
            source_provider=self.name,
            content=result,
            session_id=session_id,
            task_id=task_id,
            summary=result.get("reply") or result.get("summary"),
            created_by=self.name,
        )


class ProviderRegistry:
    """Registry for external AI providers and local orchestration clients."""

    def __init__(self) -> None:
        self._providers: Dict[str, BaseProviderAdapter] = {}

    def register(self, provider: BaseProviderAdapter) -> None:
        logger.debug("Registering provider %s", provider.name)
        self._providers[provider.name] = provider

    def get(self, name: str) -> BaseProviderAdapter:
        key = name.lower().strip()
        if key not in self._providers:
            raise KeyError(f"Provider not registered: {name}")
        return self._providers[key]

    def has_provider(self, name: str) -> bool:
        return name.lower().strip() in self._providers

    def names(self) -> List[str]:
        return sorted(self._providers)

    def status(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        openrouter_key = bool(os.getenv("OPENROUTER_API_KEY"))
        provider_key_env = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "cursor": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "minimax": "MINIMAX_API_KEY",
            "grok": "GROK_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY",
            "hermes": "HERMES_API_KEY",
            "openclaw": "OPENCLAW_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        for name in self.names():
            provider = self.get(name)
            model_env = provider.model_env or f"OPENROUTER_MODEL_{name.upper()}"
            key_env = provider_key_env.get(name, "")
            items.append(
                {
                    "name": name,
                    "enabled": provider.enabled,
                    "openrouter_configured": openrouter_key,
                    "provider_key_env": key_env,
                    "provider_key_configured": bool(os.getenv(key_env)) if key_env else False,
                    "model_env": model_env,
                    "model": os.getenv(model_env, provider.default_openrouter_model),
                }
            )
        return items

    def choose_provider(self, prompt: str, *, preferred: Optional[str] = None) -> str:
        if preferred and self.has_provider(preferred):
            return preferred.lower().strip()
        lower = prompt.lower()
        if any(word in lower for word in ["code", "coding", "repo", "bug", "claude", "cursor"]):
            return "claude" if self.has_provider("claude") else "cursor"
        if any(word in lower for word in ["search", "research", "news", "perplexity", "grok"]):
            if self.has_provider("perplexity"):
                return "perplexity"
            if self.has_provider("grok"):
                return "grok"
        if any(word in lower for word in ["batch", "cheap", "大量", "批量"]):
            return "deepseek" if self.has_provider("deepseek") else "minimax"
        if any(word in lower for word in ["openclaw", "hermes", "orchestrate", "tool"]):
            return "openclaw" if self.has_provider("openclaw") else "hermes"
        if self.has_provider("openai"):
            return "openai"
        return self.names()[0]

    def run(
        self,
        *,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        preferred: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        provider_name = self.choose_provider(prompt, preferred=preferred)
        provider = self.get(provider_name)
        result = provider.run(prompt, context=context)
        provider.write_context(result, session_id=session_id, task_id=task_id)
        return result


def register_default_providers(registry: ProviderRegistry, providers: Iterable[BaseProviderAdapter]) -> None:
    for provider in providers:
        registry.register(provider)
