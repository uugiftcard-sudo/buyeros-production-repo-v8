"""E-commerce buyers service with Shopify and custom REST fallbacks."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .adapters.shopify_adapter import ShopifyAdapter
from .adapters.custom_ecom_adapter import CustomEcomAdapter

logger = logging.getLogger(__name__)


class BuyersService:
    """Read buyer profiles from the first configured provider (Shopify → custom REST)."""

    def __init__(self) -> None:
        self._providers: List[tuple[str, Any]] = []
        self._init_providers()

    def _init_providers(self) -> None:
        shopify = ShopifyAdapter()
        if shopify.configured():
            self._providers.append(("shopify", shopify))
            logger.info("Buyers service: Shopify is configured")

        custom = CustomEcomAdapter()
        if custom.configured():
            self._providers.append(("custom", custom))
            logger.info("Buyers service: Custom REST is configured")

        if not self._providers:
            logger.warning("No buyers providers configured — buyers will return empty data")

    def configured(self) -> bool:
        return bool(self._providers)

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        for name, provider in self._providers:
            try:
                return provider.get_customer(customer_id)
            except Exception as exc:
                logger.error("get_customer failed via %s for %s: %s", name, customer_id, exc)
                continue
        return self._empty_customer(customer_id)

    def list_customers(self, limit: int = 20) -> List[Dict[str, Any]]:
        for name, provider in self._providers:
            try:
                return provider.list_customers(limit=limit)
            except Exception as exc:
                logger.error("list_customers failed via %s: %s", name, exc)
                continue
        return []

    def _empty_customer(self, customer_id: str) -> Dict[str, Any]:
        return {
            "customer_id": customer_id,
            "error": "no_provider_configured",
            "message": "買家服務未配置，請聯繫管理員。",
        }
