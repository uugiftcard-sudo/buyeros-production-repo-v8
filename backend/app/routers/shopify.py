"""
Shopify router — /shopify/*

All endpoints require Bearer API key (verify_api_key dependency).

Routes:
  GET  /shopify/status
  GET  /shopify/products
  GET  /shopify/products/{product_id}
  POST /shopify/products
  POST /shopify/products/{product_id}/status
  GET  /shopify/orders
  GET  /shopify/orders/{order_id}
  POST /shopify/orders
  GET  /shopify/collections/summary
  POST /shopify/products/{product_id}/score      ← ProofScore
  POST /shopify/products/{product_id}/check      ← Claim Defence full check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies import verify_api_key  # existing dep
from app.services import claim_defence as cd
from app.services import proof_score as ps
from app.services import shopify_connector as shopify

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shopify", tags=["shopify"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateProductRequest(BaseModel):
    title: str
    brand: str
    category: str
    collection: str = "luxury"
    price_hkd: float
    condition: str = "used"
    authenticity_verified: bool = False
    proof_images: list[str] = Field(default_factory=list)
    sku: str = ""
    market: list[str] = Field(default_factory=lambda: ["hk", "uk"])


class UpdateProductStatusRequest(BaseModel):
    status: str   # active | draft | archived


class CreateOrderRequest(BaseModel):
    product_id: str
    market: str = "hk"
    buyer_email: str = ""
    shipping_address: dict[str, Any] = Field(default_factory=dict)


class ClaimCheckRequest(BaseModel):
    caption: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def shopify_status(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Connector health and config status."""
    return shopify.status()


@router.get("/products")
async def list_products(
    collection: str | None = Query(None, description="luxury | budget"),
    market: str = Query("hk", description="hk | uk"),
    limit: int = Query(50, ge=1, le=200),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """List products filtered by collection and market."""
    products = shopify.list_products(collection=collection, market=market, limit=limit)
    return {"products": products, "count": len(products), "market": market}


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    market: str = Query("hk"),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Fetch a single product by ID."""
    product = shopify.get_product(product_id=product_id, market=market)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.post("/products", status_code=201)
async def create_product(
    body: CreateProductRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Create a new product in the catalogue."""
    product = shopify.create_product(
        title=body.title,
        brand=body.brand,
        category=body.category,
        collection=body.collection,
        price_hkd=body.price_hkd,
        condition=body.condition,
        authenticity_verified=body.authenticity_verified,
        proof_images=body.proof_images,
        sku=body.sku,
        market=body.market,
    )
    return {"created": True, "product": product}


@router.post("/products/{product_id}/status")
async def update_product_status(
    product_id: str,
    body: UpdateProductStatusRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Set product status (active | draft | archived)."""
    valid = {"active", "draft", "archived"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    updated = shopify.update_product_status(product_id=product_id, status=body.status)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {"updated": True, "product": updated}


@router.get("/orders")
async def list_orders(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """List orders, optionally filtered by status."""
    orders = shopify.list_orders(status=status, limit=limit)
    return {"orders": orders, "count": len(orders)}


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Fetch a single order."""
    order = shopify.get_order(order_id=order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.post("/orders", status_code=201)
async def create_order(
    body: CreateOrderRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Simulate placing a new order."""
    order = shopify.create_order(
        product_id=body.product_id,
        market=body.market,
        buyer_email=body.buyer_email,
        shipping_address=body.shipping_address,
    )
    if order is None:
        raise HTTPException(status_code=404, detail=f"Product {body.product_id} not found")
    return {"created": True, "order": order}


@router.get("/collections/summary")
async def collection_summary(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Aggregate stats across collections."""
    return shopify.get_collection_summary()


@router.post("/products/{product_id}/score")
async def proof_score_product(
    product_id: str,
    market: str = Query("hk"),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Run ProofScore on a product."""
    product = shopify.get_product(product_id=product_id, market=market)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    result = ps.score(product)
    return result.to_dict()


@router.post("/products/{product_id}/check")
async def claim_defence_check(
    product_id: str,
    body: ClaimCheckRequest,
    market: str = Query("hk"),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """
    Run the full Claim Defence pipeline on a product.
    Optionally include a caption/ad copy to scan alongside product fields.
    Also runs ProofScore and triggers Founder Approval Gate if needed.
    """
    product = shopify.get_product(product_id=product_id, market=market)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    # ProofScore
    score_result = ps.score(product)
    score_dict = score_result.to_dict()

    # Claim Defence
    check_result = cd.full_check(
        product=product,
        caption=body.caption,
        proof_score=score_dict,
    )

    return {
        "product_id": product_id,
        "proof_score": score_dict,
        "claim_defence": check_result,
        "listing_safe": score_result.listing_safe and not check_result["listing_blocked"],
        "gate_triggered": check_result["gate_triggered"],
    }
