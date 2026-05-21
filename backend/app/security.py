"""Lightweight API-key protection for public BuyerOS endpoints."""

from __future__ import annotations

import os

from fastapi import HTTPException, Request


async def require_api_key(request: Request) -> None:
    """Require an API key only when BUYEROS_API_KEY is configured.

    This keeps local tests and private development frictionless while making
    production deployment safe by setting one env var.
    """

    expected = os.getenv("BUYEROS_API_KEY")
    if not expected:
        return
    supplied = request.headers.get("x-buyeros-api-key")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        supplied = auth.split(" ", 1)[1].strip()
    if supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing BuyerOS API key")

