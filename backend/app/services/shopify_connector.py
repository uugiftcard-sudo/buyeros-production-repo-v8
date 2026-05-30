"""
Shopify connector — mock mode by default.

Real mode activates when SHOPIFY_API_KEY, SHOPIFY_STORE_URL, and
SHOPIFY_ACCESS_TOKEN env vars are present.

Generates realistic fake data in mock mode for development / testing.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
import os
import random
import uuid
from datetime import UTC, datetime
from typing import Any

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "https://buyeros.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

MOCK_MODE = not SHOPIFY_ACCESS_TOKEN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).isoformat()


def _fake_id(prefix: str = "gid://shopify/Product") -> str:
    return f"{prefix}/{random.randint(1000000, 9999999)}"


BRANDS_LUXURY = [
    "Louis Vuitton", "Chanel", "Hermès", "Rolex", "Patek Philippe",
    "Cartier", "Gucci", "Prada", "Dior", "Bottega Veneta",
    "Balenciaga", "Saint Laurent", "Celine", "Givenchy", "Fendi",
    "Burberry", "Moncler", "Canada Goose", "Balenciaga", "Versace",
]

BRANDS_BUDGET = [
    "Coach", "Michael Kors", "Kate Spade", "Tory Burch",
    "Marc Jacobs", "Longchamp", "Mulberry", "Ted Baker",
]

CATEGORIES = ["bag", "watch", "wallet", "belt", "shoes", "clothing", "accessory"]

COLLECTIONS = ["luxury", "budget", "vintage", "limited"]

MARKETS = ["hk", "uk", "cn", "sg"]

CONDITIONS = ["new", "like_new", "excellent", "very_good", "good", "used"]


def _mock_product(
    product_id: str | None = None,
    collection: str = "luxury",
    market: str = "hk",
) -> dict[str, Any]:
    brand = random.choice(BRANDS_LUXURY if collection == "luxury" else BRANDS_BUDGET)
    base_price = random.randint(500, 50000)
    return {
        "id": product_id or _fake_id(),
        "title": f"{brand} {random.choice(CATEGORIES).title()}",
        "brand": brand,
        "category": random.choice(CATEGORIES),
        "collection": collection,
        "price_hkd": base_price,
        "price_GBP": round(base_price * 0.081, 2),
        "condition": random.choice(CONDITIONS),
        "authenticity_verified": random.choice([True, True, True, False]),
        "proof_images": [f"https://cdn.buyeros.com/proof/{uuid.uuid4().hex[:8]}.jpg"
                        for _ in range(random.randint(0, 5))],
        "sku": f"{brand[:3].upper()}-{random.randint(1000, 9999)}",
        "market": market,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _mock_order(product_id: str, market: str = "hk") -> dict[str, Any]:
    return {
        "id": _fake_id("gid://shopify/Order"),
        "product_id": product_id,
        "market": market,
        "status": random.choice(["pending", "processing", "shipped", "delivered"]),
        "buyer_email": f"buyer{random.randint(100, 999)}@example.com",
        "shipping_address": {
            "name": f"Customer {random.randint(1, 999)}",
            "city": "Hong Kong" if market == "hk" else "London",
            "country": "HK" if market == "hk" else "UK",
        },
        "created_at": _now(),
    }


# ---------------------------------------------------------------------------
# Public API (mock + real gateway)
# ---------------------------------------------------------------------------

def status() -> dict[str, Any]:
    return {
        "mode": "mock" if MOCK_MODE else "live",
        "store_url": SHOPIFY_STORE_URL,
        "shopify_connected": bool(SHOPIFY_ACCESS_TOKEN),
    }


def list_products(
    collection: str | None = None,
    market: str = "hk",
    limit: int = 50,
) -> list[dict[str, Any]]:
    if MOCK_MODE:
        return [_mock_product(collection=collection or "luxury", market=market)
                for _ in range(limit)]
    # Real mode: implement Shopify Admin API call here
    raise NotImplementedError("Live Shopify integration not yet implemented")


def get_product(product_id: str, market: str = "hk") -> dict[str, Any] | None:
    if MOCK_MODE:
        # Return a product with the given ID
        return _mock_product(product_id=product_id, market=market)
    raise NotImplementedError("Live Shopify integration not yet implemented")


def create_product(
    title: str,
    brand: str,
    category: str,
    collection: str = "luxury",
    price_hkd: float = 0.0,
    condition: str = "used",
    authenticity_verified: bool = False,
    proof_images: list[str] | None = None,
    sku: str = "",
    market: str = "hk",
) -> dict[str, Any]:
    if MOCK_MODE:
        product = _mock_product(collection=collection, market=market)
        product.update(
            title=title, brand=brand, category=category,
            price_hkd=price_hkd, condition=condition,
            authenticity_verified=authenticity_verified,
            proof_images=proof_images or [],
            sku=sku,
        )
        return product
    raise NotImplementedError("Live Shopify integration not yet implemented")


def update_product_status(product_id: str, status: str) -> dict[str, Any] | None:
    if MOCK_MODE:
        return {"id": product_id, "status": status, "updated_at": _now()}
    raise NotImplementedError("Live Shopify integration not yet implemented")


def list_orders(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if MOCK_MODE:
        mock_products = [_mock_product() for _ in range(5)]
        orders = [_mock_order(p["id"]) for p in mock_products]
        if status:
            orders = [o for o in orders if o["status"] == status]
        return orders[:limit]
    raise NotImplementedError("Live Shopify integration not yet implemented")


def get_order(order_id: str) -> dict[str, Any] | None:
    if MOCK_MODE:
        return {
            "id": order_id,
            "product_id": _fake_id(),
            "status": "pending",
            "created_at": _now(),
        }
    raise NotImplementedError("Live Shopify integration not yet implemented")


def create_order(
    product_id: str,
    market: str = "hk",
    buyer_email: str = "",
    shipping_address: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if MOCK_MODE:
        return _mock_order(product_id=product_id, market=market)
    raise NotImplementedError("Live Shopify integration not yet implemented")


def get_collection_summary() -> dict[str, Any]:
    if MOCK_MODE:
        return {
            "luxury": {"count": random.randint(50, 200), "avg_price": 15000},
            "budget": {"count": random.randint(20, 100), "avg_price": 2500},
            "vintage": {"count": random.randint(10, 50), "avg_price": 8000},
            "limited": {"count": random.randint(5, 30), "avg_price": 25000},
        }
    raise NotImplementedError("Live Shopify integration not yet implemented")
