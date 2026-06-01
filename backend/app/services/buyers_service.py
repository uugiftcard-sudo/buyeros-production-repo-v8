"""Buyer/customer service with local fallback data."""

from __future__ import annotations

from typing import Any


class BuyersService:
    def configured(self) -> bool:
        return False

    def list_customers(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return [
            {"customer_id": "cust-1", "name": "陳大文", "tier": "VIP"},
            {"customer_id": "cust-2", "name": "王小美", "tier": "standard"},
        ][:limit]

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        for customer in self.list_customers(limit=100):
            if customer["customer_id"] == customer_id:
                return customer
        return {"customer_id": customer_id, "error": "not_found"}
