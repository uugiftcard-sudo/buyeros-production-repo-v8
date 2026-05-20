"""E-commerce orders service with Shopify and custom REST fallbacks."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .adapters.shopify_adapter import ShopifyAdapter
from .adapters.custom_ecom_adapter import CustomEcomAdapter

logger = logging.getLogger(__name__)


class OrdersService:
    """Read orders from the first configured provider (Shopify → custom REST)."""

    def __init__(self) -> None:
        self._providers: List[tuple[str, Any]] = []
        self._init_providers()

    def _init_providers(self) -> None:
        shopify = ShopifyAdapter()
        if shopify.configured():
            self._providers.append(("shopify", shopify))
            logger.info("Orders service: Shopify is configured")

        custom = CustomEcomAdapter()
        if custom.configured():
            self._providers.append(("custom", custom))
            logger.info("Orders service: Custom REST is configured")

        if not self._providers:
            logger.warning("No orders providers configured — orders will return empty data")

    def configured(self) -> bool:
        return bool(self._providers)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        for name, provider in self._providers:
            try:
                return provider.get_order(order_id)
            except Exception as exc:
                logger.error("get_order failed via %s for %s: %s", name, order_id, exc)
                continue
        return self._empty_order(order_id)

    def list_orders(
        self,
        *,
        customer_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        for name, provider in self._providers:
            try:
                return provider.list_orders(customer_id=customer_id, limit=limit)
            except Exception as exc:
                logger.error("list_orders failed via %s: %s", name, exc)
                continue
        return []

    def _empty_order(self, order_id: str) -> Dict[str, Any]:
        return {
            "order_id": order_id,
            "error": "no_provider_configured",
            "message": "訂單服務未配置，請聯繫管理員。",
        }
