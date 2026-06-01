"""Metrics router for Prometheus scraping."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
