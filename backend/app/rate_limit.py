"""Rate limiting configuration for BuyerOS API."""

from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on API key or IP."""
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return api_key
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "retry_after": getattr(exc, "retry_after", 60),
        },
    )


# Rate limits
DEFAULT_LIMIT = "100/minute"
AUTHENTICATED_LIMIT = "500/minute"
WRITE_LIMIT = "30/minute"
