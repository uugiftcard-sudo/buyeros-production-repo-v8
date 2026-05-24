"""CLOTH API integration for commerce live-selling plans.

This module provides a typed client for calling CLOTH's AI live commerce APIs:
- GET  /api/live/readiness     — check live-selling readiness
- POST /api/live/selling-plan — generate AI virtual host selling plan
- GET  /api/finance/*        — finance CRUD
- GET  /api/inventory/*       — inventory management
- GET  /api/support/*         — support tickets & FAQs
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class CLOTHConfig:
    """CLOTH API configuration."""
    base_url: str = "http://localhost:3001"  # default dev URL
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "CLOTHConfig":
        return cls(
            base_url=os.environ.get("CLOTH_BASE_URL", "http://localhost:3001"),
            timeout=float(os.environ.get("CLOTH_TIMEOUT", "30.0")),
        )


@dataclass
class InventoryCheck:
    """Inventory status check result."""
    status: str  # "ready" | "out_of_stock" | "unknown"
    sku: str = ""
    message: str = ""


@dataclass
class FinanceCheck:
    """Finance estimate for live-selling plan."""
    expectedRevenue: int = 0
    estimatedPlatformFee: int = 0
    estimatedAdCost: int = 0
    estimatedInventoryCost: int = 0
    estimatedRefundReserve: int = 0
    estimatedNetProfit: int = 0


@dataclass
class LiveSellingPlan:
    """AI virtual host selling plan from CLOTH."""
    planId: str = ""
    productId: str = ""
    productTitle: str = ""
    accountStyle: str = "educational"
    hook: str = ""
    script: str = ""
    interactionPrompts: List[str] = None
    cta: str = ""
    inventoryCheck: Optional[InventoryCheck] = None
    financeCheck: Optional[FinanceCheck] = None
    supportNotes: List[str] = None
    safetyNote: str = ""
    createdAt: str = ""

    def __post_init__(self) -> None:
        if self.interactionPrompts is None:
            self.interactionPrompts = []
        if self.supportNotes is None:
            self.supportNotes = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.planId,
            "product_id": self.productId,
            "product_title": self.productTitle,
            "account_style": self.accountStyle,
            "hook": self.hook,
            "script": self.script,
            "interaction_prompts": self.interactionPrompts,
            "cta": self.cta,
            "inventory_check": {
                "status": self.inventoryCheck.status if self.inventoryCheck else "unknown",
                "sku": self.inventoryCheck.sku if self.inventoryCheck else "",
                "message": self.inventoryCheck.message if self.inventoryCheck else "",
            },
            "finance_check": {
                "expected_revenue": self.financeCheck.expectedRevenue if self.financeCheck else 0,
                "estimated_platform_fee": self.financeCheck.estimatedPlatformFee if self.financeCheck else 0,
                "estimated_ad_cost": self.financeCheck.estimatedAdCost if self.financeCheck else 0,
                "estimated_inventory_cost": self.financeCheck.estimatedInventoryCost if self.financeCheck else 0,
                "estimated_refund_reserve": self.financeCheck.estimatedRefundReserve if self.financeCheck else 0,
                "estimated_net_profit": self.financeCheck.estimatedNetProfit if self.financeCheck else 0,
            } if self.financeCheck else {},
            "support_notes": self.supportNotes,
            "safety_note": self.safetyNote,
            "created_at": self.createdAt,
        }


@dataclass
class ReadinessResult:
    """Live-selling readiness check result."""
    ready: bool
    sellableCount: int
    checks: List[str]
    safetyNote: str = ""


@dataclass
class CLOTHIntegrationResult:
    """Result of CLOTH API call."""
    ok: bool
    data: Any = None
    error: str = ""
    provider: str = "cloth"


class CLOTHIntegration:
    """Client for CLOTH AI Live Commerce APIs.

    Usage:
        config = CLOTHConfig.from_env()
        client = CLOTHIntegration(config)

        readiness = client.check_readiness()
        plan = client.generate_selling_plan(product_id="prod-001", account_style="luxury_editor")
    """

    def __init__(self, config: Optional[CLOTHConfig] = None) -> None:
        self.config = config or CLOTHConfig.from_env()
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
        """POST to CLOTH API with error handling."""
        try:
            resp = self.client.post(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.TimeoutException:
            return {"error": "CLOTH API timeout"}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """GET from CLOTH API with error handling."""
        try:
            resp = self.client.get(path, params=params or {})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.TimeoutException:
            return {"error": "CLOTH API timeout"}
        except Exception as e:
            return {"error": str(e)}

    def check_readiness(self) -> CLOTHIntegrationResult:
        """Check if live-selling is ready (has sellable products, etc.).

        Returns:
            CLOTHIntegrationResult with ReadinessResult in .data
        """
        result = self._get("/api/live/readiness")

        if "error" in result:
            return CLOTHIntegrationResult(ok=False, error=result["error"])

        readiness = ReadinessResult(
            ready=result.get("ready", False),
            sellableCount=result.get("sellableCount", 0),
            checks=result.get("checks", []),
            safetyNote=result.get("safetyNote", ""),
        )

        return CLOTHIntegrationResult(ok=True, data=readiness, provider="cloth")

    def generate_selling_plan(
        self,
        *,
        product_id: Optional[str] = None,
        account_style: str = "educational",
        cta: Optional[str] = None,
    ) -> CLOTHIntegrationResult:
        """Generate an AI virtual host selling plan.

        Args:
            product_id: Specific product SKU (optional)
            account_style: "educational" | "luxury_editor" | "deal_hunter" | "community_host"
            cta: Custom call-to-action text

        Returns:
            CLOTHIntegrationResult with LiveSellingPlan in .data
        """
        payload: Dict[str, Any] = {
            "accountStyle": account_style,
        }
        if product_id:
            payload["productId"] = product_id
        if cta:
            payload["cta"] = cta

        result = self._post("/api/live/selling-plan", payload)

        if "error" in result:
            return CLOTHIntegrationResult(ok=False, error=result["error"])

        inv_raw = result.get("inventoryCheck", {})
        inv_check = InventoryCheck(
            status=inv_raw.get("status", "unknown"),
            sku=inv_raw.get("sku", ""),
            message=inv_raw.get("message", ""),
        )

        fin_raw = result.get("financeCheck", {})
        fin_check = FinanceCheck(
            expectedRevenue=fin_raw.get("expectedRevenue", 0),
            estimatedPlatformFee=fin_raw.get("estimatedPlatformFee", 0),
            estimatedAdCost=fin_raw.get("estimatedAdCost", 0),
            estimatedInventoryCost=fin_raw.get("estimatedInventoryCost", 0),
            estimatedRefundReserve=fin_raw.get("estimatedRefundReserve", 0),
            estimatedNetProfit=fin_raw.get("estimatedNetProfit", 0),
        )

        plan = LiveSellingPlan(
            planId=result.get("planId", ""),
            productId=result.get("productId", ""),
            productTitle=result.get("productTitle", ""),
            accountStyle=result.get("accountStyle", "educational"),
            hook=result.get("hook", ""),
            script=result.get("script", ""),
            interactionPrompts=result.get("interactionPrompts", []),
            cta=result.get("cta", ""),
            inventoryCheck=inv_check,
            financeCheck=fin_check,
            supportNotes=result.get("supportNotes", []),
            safetyNote=result.get("safetyNote", ""),
            createdAt=result.get("createdAt", ""),
        )

        return CLOTHIntegrationResult(ok=True, data=plan, provider="cloth")

    def get_inventory(self, limit: int = 50) -> CLOTHIntegrationResult:
        """Get current inventory list."""
        result = self._get("/api/inventory", {"limit": str(limit)})
        if "error" in result:
            return CLOTHIntegrationResult(ok=False, error=result["error"])
        return CLOTHIntegrationResult(ok=True, data=result, provider="cloth")

    def get_finance_summary(self, period: Optional[str] = None) -> CLOTHIntegrationResult:
        """Get finance summary for a period."""
        params = {}
        if period:
            params["period"] = period
        result = self._get("/api/finance/summary", params)
        if "error" in result:
            return CLOTHIntegrationResult(ok=False, error=result["error"])
        return CLOTHIntegrationResult(ok=True, data=result, provider="cloth")

    def get_support_faqs(self) -> CLOTHIntegrationResult:
        """Get support FAQs."""
        result = self._get("/api/support/faqs")
        if "error" in result:
            return CLOTHIntegrationResult(ok=False, error=result["error"])
        return CLOTHIntegrationResult(ok=True, data=result, provider="cloth")

    def is_available(self) -> bool:
        """Check if CLOTH API is reachable."""
        try:
            resp = self.client.get("/api/live/readiness", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def __enter__(self) -> "CLOTHIntegration":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
