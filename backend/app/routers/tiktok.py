"""
TikTok router — /tiktok/*

All endpoints require Bearer API key (verify_api_key dependency).

Routes:
  POST /tiktok/video-pack      — Generate structured video content pack
  POST /tiktok/live-script     — Build TikTok Live streaming script
  POST /tiktok/ads-brief       — Build TikTok ads creative brief
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import verify_api_key
from app.services import tiktok_connector as tt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tiktok", tags=["tiktok"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class VideoPackRequest(BaseModel):
    product_id: str
    market: str = "hk"
    product: dict[str, Any] | None = None


class LiveScriptRequest(BaseModel):
    product_ids: list[str]
    duration_mins: int = Field(default=30, ge=5, le=120)
    market: str = "hk"
    products: list[dict[str, Any]] | None = None


class AdsBriefRequest(BaseModel):
    product_id: str
    objective: str = "sales"  # sales | traffic | awareness
    budget_hkd: float = Field(default=500.0, ge=50)
    market: str = "hk"
    product: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/video-pack")
async def generate_video_pack(
    req: VideoPackRequest,
    _key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Generate a structured video content pack for a product."""
    logger.info("/tiktok/video-pack product=%s market=%s", req.product_id, req.market)
    return tt.generate_video_pack(req.product, req.market)


@router.post("/live-script")
async def build_live_script(
    req: LiveScriptRequest,
    _key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Build a TikTok Live streaming script."""
    logger.info(
        "/tiktok/live-script products=%d duration=%dm market=%s",
        len(req.product_ids), req.duration_mins, req.market,
    )
    return tt.build_live_script(req.products, req.duration_mins, req.market)


@router.post("/ads-brief")
async def build_ads_brief(
    req: AdsBriefRequest,
    _key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Build a TikTok ads creative brief."""
    logger.info(
        "/tiktok/ads-brief product=%s objective=%s budget=%s market=%s",
        req.product_id, req.objective, req.budget_hkd, req.market,
    )
    return tt.build_ads_brief(req.product, req.objective, req.budget_hkd, req.market)
