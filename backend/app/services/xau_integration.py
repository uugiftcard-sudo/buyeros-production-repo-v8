"""XAU API integration for live streaming scripts and news alerts.

This module provides a typed client for calling XAU's AI live commerce APIs:
- POST /api/ai/script      — generate live stream scripts
- POST /api/ai/signal-interpretation — interpret trading signals
- GET  /api/news/latest    — fetch latest news for live room
- GET  /api/news/alerts    — fetch breaking news alerts
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class XAUConfig:
    """XAU API configuration."""
    base_url: str = "http://localhost:3000"  # default dev URL
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "XAUConfig":
        return cls(
            base_url=os.environ.get("XAU_BASE_URL", "http://localhost:3000"),
            timeout=float(os.environ.get("XAU_TIMEOUT", "30.0")),
        )


@dataclass
class ScriptSegments:
    """Parsed script segments from XAU /api/ai/script."""
    hook: str = ""
    story: str = ""
    interaction: str = ""
    cta: str = ""
    risk: str = ""
    style: str = "educational"
    safety: str = ""


@dataclass
class ScriptResult:
    """Result from XAU /api/ai/script."""
    script: str
    segments: ScriptSegments
    source: str  # "llm" | "cache" | "fallback"
    cached: bool = False
    bias_type: str = "wait"


@dataclass
class NewsAlert:
    """Single news alert item."""
    id: str
    headline: str
    source: str
    impact: str  # "high" | "medium" | "low"
    timestamp: str
    summary: str = ""


@dataclass
class XAUIntegrationResult:
    """Result of XAU API call."""
    ok: bool
    data: Any = None
    error: str = ""
    provider: str = "xau"


class XAUIntegration:
    """Client for XAU AI Live Commerce APIs.

    Usage:
        config = XAUConfig.from_env()
        client = XAUIntegration(config)
        result = client.generate_script(bias_type="up", topic="今日黄金直播")
    """

    def __init__(self, config: Optional[XAUConfig] = None) -> None:
        self.config = config or XAUConfig.from_env()
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST to XAU API with error handling."""
        try:
            resp = self.client.post(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.TimeoutException:
            return {"error": "XAU API timeout"}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """GET from XAU API with error handling."""
        try:
            resp = self.client.get(path, params=params or {})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.TimeoutException:
            return {"error": "XAU API timeout"}
        except Exception as e:
            return {"error": str(e)}

    def generate_script(
        self,
        *,
        bias_type: str = "wait",
        momentum: int = 50,
        position: int = 50,
        risk: int = 50,
        support: Optional[str] = None,
        resistance: Optional[str] = None,
        topic: Optional[str] = None,
        cta: Optional[str] = None,
        account_style: str = "educational",
        force_refresh: bool = False,
    ) -> XAUIntegrationResult:
        """Generate a live streaming script from XAU.

        Args:
            bias_type: "up" | "down" | "wait"
            momentum: 0-100 momentum score
            position: 0-100 position score
            risk: 0-100 risk score
            support: Key support level
            resistance: Key resistance level
            topic: Live stream topic/theme
            cta: Call-to-action text
            account_style: "educational" | "signal" | "mixed"
            force_refresh: Skip cache

        Returns:
            XAUIntegrationResult with ScriptResult in .data
        """
        payload = {
            "biasType": bias_type,
            "momentum": momentum,
            "position": position,
            "risk": risk,
            "forceRefresh": force_refresh,
        }
        if topic:
            payload["topic"] = topic
        if cta:
            payload["cta"] = cta
        if support:
            payload["support"] = support
        if resistance:
            payload["resistance"] = resistance
        payload["accountStyle"] = account_style

        result = self._post("/api/ai/script", payload)

        if "error" in result:
            return XAUIntegrationResult(ok=False, error=result["error"])

        segments_raw = result.get("segments", {})
        segments = ScriptSegments(
            hook=segments_raw.get("hook", ""),
            story=segments_raw.get("story", ""),
            interaction=segments_raw.get("interaction", ""),
            cta=segments_raw.get("cta", ""),
            risk=segments_raw.get("risk", ""),
            style=segments_raw.get("style", "educational"),
            safety=segments_raw.get("safety", ""),
        )

        script_result = ScriptResult(
            script=result.get("script", ""),
            segments=segments,
            source=result.get("source", "unknown"),
            cached=result.get("cached", False),
            bias_type=bias_type,
        )

        return XAUIntegrationResult(ok=True, data=script_result, provider="xau")

    def interpret_signal(
        self,
        *,
        signal_type: str,
        confidence: int = 60,
        zone: Optional[str] = None,
    ) -> XAUIntegrationResult:
        """Get signal interpretation from XAU.

        Args:
            signal_type: "up" | "down" | "wait"
            confidence: 0-100 confidence level
            zone: Key price zone

        Returns:
            XAUIntegrationResult with interpretation text in .data
        """
        payload = {
            "signalType": signal_type,
            "confidence": confidence,
        }
        if zone:
            payload["zone"] = zone

        result = self._post("/api/ai/signal-interpretation", payload)

        if "error" in result:
            return XAUIntegrationResult(ok=False, error=result["error"])

        return XAUIntegrationResult(
            ok=True,
            data=result.get("interpretation", ""),
            provider="xau",
        )

    def get_latest_news(self) -> XAUIntegrationResult:
        """Fetch latest news for live room display.

        Returns:
            XAUIntegrationResult with list of news items in .data
        """
        result = self._get("/api/news/latest")

        if "error" in result:
            return XAUIntegrationResult(ok=False, error=result["error"])

        return XAUIntegrationResult(ok=True, data=result, provider="xau")

    def get_news_alerts(self) -> XAUIntegrationResult:
        """Fetch breaking news alerts for live room.

        Returns:
            XAUIntegrationResult with list of NewsAlert in .data
        """
        result = self._get("/api/news/alerts")

        if "error" in result:
            return XAUIntegrationResult(ok=False, error=result["error"])

        alerts = [
            NewsAlert(
                id=item.get("id", ""),
                headline=item.get("headline", ""),
                source=item.get("source", ""),
                impact=item.get("impact", "low"),
                timestamp=item.get("timestamp", ""),
                summary=item.get("summary", ""),
            )
            for item in result.get("alerts", [])
        ]

        return XAUIntegrationResult(ok=True, data=alerts, provider="xau")

    def get_state(self) -> XAUIntegrationResult:
        """Get current live room state (topic, cta, presenter, etc.).

        Returns:
            XAUIntegrationResult with state dict in .data
        """
        result = self._get("/api/state")

        if "error" in result:
            return XAUIntegrationResult(ok=False, error=result["error"])

        return XAUIntegrationResult(ok=True, data=result, provider="xau")

    def is_available(self) -> bool:
        """Check if XAU API is reachable."""
        try:
            resp = self.client.get("/api/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def __enter__(self) -> "XAUIntegration":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
