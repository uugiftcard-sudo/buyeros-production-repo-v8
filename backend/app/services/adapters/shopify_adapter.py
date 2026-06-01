"""Shopify Admin API adapter for orders and buyers."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


class ShopifyAdapter:
    """Read orders and customers via Shopify Admin REST API.

    Docs: https://shopify.dev/docs/admin-api/rest
    Requires: read_orders and read_customers API scopes.
    """

    def __init__(self) -> None:
        self.domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "").rstrip("/")
        self.token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
        self._base = f"https://{self.domain}/admin/api/2024-01"

    def configured(self) -> bool:
        return bool(self.domain and self.token)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json",
        }

    # ── Orders ────────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> Dict[str, Any]:
        url = f"{self._base}/orders/{order_id}.json"
        resp = requests.get(url, headers=self._headers(), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        order = data.get("order", {})
        return {
            "order_id": str(order.get("id", "")),
            "order_number": order.get("order_number", ""),
            "financial_status": order.get("financial_status", ""),
            "fulfillment_status": order.get("fulfillment_status", ""),
            "total_price": order.get("total_price", ""),
            "currency": order.get("currency", ""),
            "customer_id": str(order.get("customer", {}).get("id", "")),
            "customer_email": order.get("customer", {}).get("email", ""),
            "created_at": order.get("created_at", ""),
            "line_items": [
                {
                    "title": item.get("title", ""),
                    "quantity": item.get("quantity", 0),
                    "price": item.get("price", ""),
                }
                for item in order.get("line_items", [])
            ],
            "raw": order,
        }

    def list_orders(
        self,
        *,
        customer_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"status": "any", "limit": min(limit, 50)}
        if customer_id:
            params["customer_id"] = customer_id
        url = f"{self._base}/orders.json"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
        resp.raise_for_status()
        orders = resp.json().get("orders", [])
        return [
            {
                "order_id": str(o.get("id", "")),
                "order_number": o.get("order_number", ""),
                "financial_status": o.get("financial_status", ""),
                "total_price": o.get("total_price", ""),
                "created_at": o.get("created_at", ""),
            }
            for o in orders
        ]

    # ── Customers ─────────────────────────────────────────────────────────

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        url = f"{self._base}/customers/{customer_id}.json"
        resp = requests.get(url, headers=self._headers(), timeout=20)
        resp.raise_for_status()
        customer = resp.json().get("customer", {})
        return {
            "customer_id": str(customer.get("id", "")),
            "email": customer.get("email", ""),
            "first_name": customer.get("first_name", ""),
            "last_name": customer.get("last_name", ""),
            "phone": customer.get("phone", ""),
            "orders_count": customer.get("orders_count", 0),
            "total_spent": customer.get("total_spent", ""),
            "created_at": customer.get("created_at", ""),
            "raw": customer,
        }

    def list_customers(self, limit: int = 20) -> List[Dict[str, Any]]:
        params = {"limit": min(limit, 50)}
        url = f"{self._base}/customers.json"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
        resp.raise_for_status()
        customers = resp.json().get("customers", [])
        return [
            {
                "customer_id": str(c.get("id", "")),
                "email": c.get("email", ""),
                "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "orders_count": c.get("orders_count", 0),
                "total_spent": c.get("total_spent", ""),
            }
            for c in customers
        ]
