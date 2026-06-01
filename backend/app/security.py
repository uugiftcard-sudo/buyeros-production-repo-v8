"""BuyerOS API key dependency."""

from __future__ import annotations

import os

from fastapi import HTTPException, Request


async def require_api_key(request: Request) -> None:
    expected = os.getenv("BUYEROS_API_KEY", "").strip()
    if not expected:
        return

    bearer = request.headers.get("authorization", "")
    supplied = ""
    if bearer.lower().startswith("bearer "):
        supplied = bearer[7:].strip()
    else:
        supplied = request.headers.get("x-buyeros-api-key", "").strip()

    if supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
