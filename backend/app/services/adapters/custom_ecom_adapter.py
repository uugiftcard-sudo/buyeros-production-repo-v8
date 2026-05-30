"""Custom REST API adapter for orders and buyers (e-commerce fallback)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


class CustomEcomAdapter:
    """Read orders and buyers from a custom REST API.

    Expected contracts:
    - GET {ORDERS_API_BASE_URL}/orders/{order_id}
    - GET {ORDERS_API_BASE_URL}/orders?user_id={customer_id}&limit=N
    - GET {BUYERS_API_BASE_URL}/customers/{customer_id}
    - GET {BUYERS_API_BASE_URL}/customers?limit=N
    """

    def __init__(self) -> None:
        self.orders_base = os.getenv("ORDERS_API_BASE_URL", "").rstrip("/")
        self.orders_key = os.getenv("ORDERS_API_KEY", "")
        self.buyers_base = os.getenv("BUYERS_API_BASE_URL", "").rstrip("/")
        self.buyers_key = os.getenv("BUYERS_API_KEY", "")

    def configured(self) -> bool:
        return bool(self.orders_base and self.orders_key)

    def _headers(self, key: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # ── Orders ────────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> Dict[str, Any]:
        resp = requests.get(
            f"{self.orders_base}/orders/{order_id}",
            headers=self._headers(self.orders_key),
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def list_orders(
        self,
        *,
        customer_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if customer_id:
            params["user_id"] = customer_id
        resp = requests.get(
            f"{self.orders_base}/orders",
            headers=self._headers(self.orders_key),
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("orders", [])

    # ── Buyers ─────────────────────────────────────────────────────────────

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        resp = requests.get(
            f"{self.buyers_base}/customers/{customer_id}",
            headers=self._headers(self.buyers_key),
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def list_customers(self, limit: int = 20) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.buyers_base}/customers",
            headers=self._headers(self.buyers_key),
            params={"limit": limit},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("customers", [])
