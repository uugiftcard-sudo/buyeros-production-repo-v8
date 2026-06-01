"""Orders service with local fallback data."""

from __future__ import annotations

from typing import Any, Optional


class OrdersService:
    def configured(self) -> bool:
        return False

    def list_orders(self, *, customer_id: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
        orders = [
            {"order_id": "991", "customer_id": "cust-1", "total_hkd": 1000, "currency": "HKD", "status": "paid"},
            {"order_id": "992", "customer_id": "cust-2", "total_hkd": 680, "currency": "HKD", "status": "pending"},
        ]
        if customer_id:
            orders = [order for order in orders if order["customer_id"] == customer_id]
        return orders[:limit]

    def get_order(self, order_id: str) -> dict[str, Any]:
        for order in self.list_orders(limit=100):
            if order["order_id"] == order_id:
                return order
        return {"order_id": order_id, "error": "not_found"}
