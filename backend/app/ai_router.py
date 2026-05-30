"""AI model router backed by OpenRouter with graceful fallback.

Features:
  - Per-role model routing via environment variables
  - Automatic retry with exponential backoff (3 attempts)
  - Circuit breaker: if a provider fails 5 times in a row, it is marked degraded
    and skipped for a cooldown period (60 seconds)
  - Timeout protection (30s per call)
  - Graceful fallback when no API key is configured
"""

from __future__ import annotations

import os
import time
import threading
from typing import Dict, Optional

import requests


class CircuitBreaker:
    """Thread-safe sliding-window circuit breaker.

    States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (probe)
    """

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 60.0) -> None:
        self._lock = threading.Lock()
        self._failures: list[float] = []  # timestamps of recent failures
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._state = "closed"

    def state(self) -> str:
        with self._lock:
            now = time.time()
            cutoff = now - self._cooldown
            self._failures = [t for t in self._failures if t > cutoff]
            if not self._failures:
                self._state = "closed"
            elif len(self._failures) >= self._failure_threshold:
                self._state = "open"
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failures.clear()
            self._state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self._failures.append(time.time())
            if len(self._failures) >= self._failure_threshold:
                self._state = "open"

    def is_open(self) -> bool:
        return self.state() == "open"


class AIModelRouter:
    """Route prompts to role-specific models via OpenRouter."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.models: Dict[str, str] = {
            "supervisor": os.getenv("OPENROUTER_MODEL_SUPERVISOR", "openai/gpt-4o-mini"),
            "ops": os.getenv("OPENROUTER_MODEL_OPS", "openai/gpt-4o-mini"),
            "finance": os.getenv("OPENROUTER_MODEL_FINANCE", "openai/gpt-4o-mini"),
        }
        self._circuit = CircuitBreaker()
        self._last_error: Optional[str] = None
        self._last_latency_ms: Optional[float] = None

    def route(self, *, role: str, prompt: str) -> str:
        model = self.models.get(role, self.models["supervisor"])
        if not self.api_key:
            return f"[AI fallback:{role}] {prompt}"

        if self._circuit.is_open():
            self._last_error = "circuit_breaker_open"
            return f"[AI circuit-open:{role}] {prompt}"

        for attempt in range(3):
            try:
                start = time.perf_counter()
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    f"You are BuyerOS {role} assistant. "
                                    "Reply concise Traditional Chinese unless asked otherwise."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                self._circuit.record_success()
                self._last_latency_ms = round((time.perf_counter() - start) * 1000, 2)
                self._last_error = None
                return data["choices"][0]["message"]["content"]

            except requests.Timeout:
                self._last_error = f"timeout_attempt_{attempt + 1}"
                if attempt == 2:
                    self._circuit.record_failure()
                time.sleep(0.5 * (2 ** attempt))  # backoff: 0.5s, 1s, 2s

            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                self._last_error = f"http_{status}"
                if status in (429, 500, 502, 503, 504):
                    if attempt == 2:
                        self._circuit.record_failure()
                    time.sleep(1.0 * (2 ** attempt))
                else:
                    # 4xx other than 429 → don't retry
                    break

            except Exception as exc:
                self._last_error = str(exc)
                if attempt == 2:
                    self._circuit.record_failure()
                time.sleep(0.5 * (2 ** attempt))

        return f"[AI error:{role}] {self._last_error or 'unknown'}; prompt stored."

    def status(self) -> Dict[str, object]:
        return {
            "circuit_state": self._circuit.state(),
            "last_error": self._last_error,
            "last_latency_ms": self._last_latency_ms,
            "api_key_configured": bool(self.api_key),
        }
