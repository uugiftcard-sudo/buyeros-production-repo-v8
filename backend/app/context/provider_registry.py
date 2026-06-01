"""Provider registry and thin provider adapters for shared context."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os
import time
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
            "ok": False,
            "status": "not_configured",
            "reply": f"[{self.name}] provider key is not configured; stored task with {context_count} context item(s): {prompt}",
            "error": "provider_not_configured",
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

    FALLBACK_PROMPTS = {
        "claude": "fix code bug",
        "cursor": "fix code bug",
        "openai": "hello world",
        "gemini": "hello world",
        "deepseek": "batch process these rows",
        "minimax": "batch process these rows",
        "grok": "search latest news",
        "perplexity": "search latest news",
        "hermes": "orchestrate tools",
        "openclaw": "orchestrate tools",
        "openrouter": "hello world",
    }

    PROVIDER_KEY_ENV = {
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

    def __init__(self, *, context_hub: Optional[ContextHub] = None) -> None:
        self._providers: Dict[str, BaseProviderAdapter] = {}
        self.context_hub = context_hub

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
        for name in self.names():
            provider = self.get(name)
            model_env = provider.model_env or f"OPENROUTER_MODEL_{name.upper()}"
            key_env = self.PROVIDER_KEY_ENV.get(name, "")
            provider_key_configured = bool(os.getenv(key_env)) if key_env else False
            runtime = self._runtime_summary(name)
            configured = provider_key_configured or openrouter_key
            status = "ready"
            if not provider.enabled:
                status = "not_configured"
            elif not configured:
                status = "not_configured"
            elif runtime["last_error"] or (runtime["failure_count_24h"] > 0 and runtime["success_count_24h"] == 0):
                status = "degraded"
            items.append(
                {
                    "name": name,
                    "enabled": provider.enabled,
                    "openrouter_configured": openrouter_key,
                    "provider_key_env": key_env,
                    "provider_key_configured": provider_key_configured,
                    "model_env": model_env,
                    "model": os.getenv(model_env, provider.default_openrouter_model),
                    "fallback_target": self._fallback_target(name),
                    "last_run": runtime["last_run"],
                    "last_error": runtime["last_error"],
                    "last_latency_ms": runtime["last_latency_ms"],
                    "success_count_24h": runtime["success_count_24h"],
                    "failure_count_24h": runtime["failure_count_24h"],
                    "status": status,
                }
            )
        return items

    def choose_provider(self, prompt: str, *, preferred: Optional[str] = None) -> str:
        chain = self.fallback_chain(prompt, preferred=preferred)
        if chain:
            return chain[0]
        return self.names()[0]

    def fallback_chain(self, prompt: str, *, preferred: Optional[str] = None) -> List[str]:
        names = self.names()
        if not names:
            return []
        chain: List[str] = []
        if preferred and self.has_provider(preferred):
            chain.append(preferred.lower().strip())
        lower = prompt.lower()
        if any(word in lower for word in ["code", "coding", "repo", "bug", "claude", "cursor"]):
            chain.extend(["claude", "cursor", "openai"])
        elif any(word in lower for word in ["search", "research", "news", "perplexity", "grok"]):
            chain.extend(["perplexity", "grok", "openai"])
        elif any(word in lower for word in ["batch", "cheap", "大量", "批量"]):
            chain.extend(["deepseek", "minimax", "openai"])
        elif any(word in lower for word in ["openclaw", "hermes", "orchestrate", "tool"]):
            chain.extend(["openclaw", "hermes", "openai"])
        else:
            chain.append("openai")
        chain.extend(names)

        deduped: List[str] = []
        for name in chain:
            key = name.lower().strip()
            if key in self._providers and key not in deduped:
                deduped.append(key)
        return deduped

    def run(
        self,
        *,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        preferred: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        chain = self.fallback_chain(prompt, preferred=preferred)
        attempts: List[Dict[str, Any]] = []
        last_result: Optional[Dict[str, Any]] = None
        for index, provider_name in enumerate(chain):
            provider = self.get(provider_name)
            started_at = datetime.now(timezone.utc).isoformat()
            start_clock = time.perf_counter()
            try:
                raw_result = provider.run(prompt, context=context)
            except Exception as exc:
                logger.exception("Provider %s crashed during run", provider_name)
                raw_result = {
                    "provider": provider_name,
                    "ok": False,
                    "reply": f"[{provider_name}] provider crashed; continuing fallback.",
                    "error": str(exc),
                }
            latency_ms = round((time.perf_counter() - start_clock) * 1000, 2)
            result = self._normalize_result(
                raw_result,
                provider_name=provider_name,
                chain=chain,
                attempts=attempts,
                fallback_exhausted=index == len(chain) - 1 and not bool((raw_result or {}).get("ok")),
                preferred=preferred,
                session_id=session_id,
                task_id=task_id,
                started_at=started_at,
                latency_ms=latency_ms,
            )
            self._safe_write_context(provider, result, session_id=session_id, task_id=task_id)
            if result.get("ok"):
                return result
            attempts.append(
                {
                    "provider": provider_name,
                    "ok": False,
                    "error": result.get("error"),
                    "reply": result.get("reply"),
                }
            )
            last_result = result
        if last_result is not None:
            return last_result
        return {
            "provider": None,
            "ok": False,
            "reply": "No providers are registered.",
            "fallback_chain": [],
            "fallback_attempts": [],
            "fallback_exhausted": True,
        }

    def _normalize_result(
        self,
        result: Dict[str, Any],
        *,
        provider_name: str,
        chain: List[str],
        attempts: List[Dict[str, Any]],
        fallback_exhausted: bool,
        preferred: Optional[str],
        session_id: Optional[str],
        task_id: Optional[str],
        started_at: str,
        latency_ms: float,
    ) -> Dict[str, Any]:
        normalized = dict(result or {})
        normalized["provider"] = normalized.get("provider") or provider_name
        normalized["ok"] = bool(normalized.get("ok"))
        normalized["reply"] = normalized.get("reply") or ""
        normalized["preferred_provider"] = preferred
        normalized["selected_provider"] = normalized["provider"] if normalized["ok"] else None
        normalized["fallback_chain"] = chain
        normalized["fallback_attempts"] = attempts + [
            {
                "provider": provider_name,
                "ok": bool(normalized.get("ok")),
                "error": normalized.get("error"),
            }
        ]
        normalized["fallback_exhausted"] = fallback_exhausted
        normalized["session_id"] = session_id
        normalized["task_id"] = task_id
        normalized["created_at"] = started_at
        normalized["latency_ms"] = latency_ms
        return normalized

    def _safe_write_context(
        self,
        provider: BaseProviderAdapter,
        result: Dict[str, Any],
        *,
        session_id: Optional[str],
        task_id: Optional[str],
        ) -> None:
        try:
            provider.write_context(result, session_id=session_id, task_id=task_id)
        except Exception as exc:
            logger.exception("Provider %s failed to write context: %s", provider.name, exc)

    def _fallback_target(self, name: str) -> Optional[str]:
        prompt = self.FALLBACK_PROMPTS.get(name, "hello world")
        chain = self.fallback_chain(prompt, preferred=name)
        return chain[1] if len(chain) > 1 else None

    def _runtime_summary(self, provider_name: str) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "last_run": None,
            "last_error": None,
            "last_latency_ms": None,
            "success_count_24h": 0,
            "failure_count_24h": 0,
        }
        if self.context_hub is None:
            return summary

        entries = self.context_hub.search_context(source_provider=provider_name, limit=200)
        if not entries:
            return summary

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        latest_entry = max(entries, key=self._entry_timestamp)
        latest_runtime = self._runtime_payload(latest_entry)
        latest_error = self._last_runtime_error(latest_runtime)

        success_count = 0
        failure_count = 0
        for entry in entries:
            timestamp = self._entry_datetime(entry)
            if timestamp is None or timestamp < cutoff:
                continue
            runtime = self._runtime_payload(entry)
            if runtime.get("ok") is True:
                success_count += 1
                continue
            error = self._last_runtime_error(runtime)
            if error and error != "provider_not_configured":
                failure_count += 1

        summary.update(
            {
                "last_run": latest_entry.get("created_at"),
                "last_error": None if latest_error == "provider_not_configured" else latest_error,
                "last_latency_ms": latest_runtime.get("latency_ms"),
                "success_count_24h": success_count,
                "failure_count_24h": failure_count,
            }
        )
        return summary

    def _runtime_payload(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        content = entry.get("content") or {}
        runtime = content.get("content") if isinstance(content, dict) else {}
        return runtime if isinstance(runtime, dict) else {}

    def _last_runtime_error(self, runtime: Dict[str, Any]) -> Optional[str]:
        error = runtime.get("error")
        if error:
            return str(error)
        if runtime.get("ok") is True:
            return None
        for attempt in runtime.get("fallback_attempts") or []:
            attempt_error = (attempt or {}).get("error")
            if attempt_error:
                return str(attempt_error)
        return None

    def _entry_datetime(self, entry: Dict[str, Any]) -> Optional[datetime]:
        raw = entry.get("created_at")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None

    def _entry_timestamp(self, entry: Dict[str, Any]) -> float:
        timestamp = self._entry_datetime(entry)
        return timestamp.timestamp() if timestamp is not None else 0.0


def register_default_providers(registry: ProviderRegistry, providers: Iterable[BaseProviderAdapter]) -> None:
    for provider in providers:
        registry.register(provider)
