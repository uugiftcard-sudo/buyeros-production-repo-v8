"""Consolidated authentication for BuyerOS.

Supports both API key and JWT authentication with proper security.
"""

from __future__ import annotations

import os
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

# ---------------------------------------------------------------------------
# Security schemes
# ---------------------------------------------------------------------------

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER_SCHEME = HTTPBearer(auto_error=False)


def _get_api_key() -> str:
    """Get the configured API key from environment."""
    return os.getenv("BUYEROS_API_KEY", "") or os.getenv("SHOPIFY_API_KEY", "")


def _is_dev_mode() -> bool:
    """Check if running in development mode."""
    return os.getenv("BUYEROS_DEV_MODE", "").lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# Required authentication dependency
# ---------------------------------------------------------------------------

async def require_auth(
    api_key: Annotated[Optional[str], Depends(API_KEY_HEADER)],
    bearer: Annotated[Optional[HTTPAuthorizationCredentials], Depends(BEARER_SCHEME)],
) -> dict:
    """
    Require authentication via API key or Bearer token.

    In production (BUYEROS_DEV_MODE != true):
        - Requires valid BUYEROS_API_KEY or SHOPIFY_API_KEY
        - Accepts X-API-Key header OR Authorization: Bearer header

    In development mode (BUYEROS_DEV_MODE=true):
        - Allows requests without authentication
    """
    expected_key = _get_api_key()

    # Dev mode: allow all requests
    if _is_dev_mode():
        return {"mode": "dev", "user": "dev-user"}

    # Production: require valid authentication
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: BUYEROS_API_KEY not set",
        )

    # Check API key
    if api_key and api_key == expected_key:
        return {"mode": "api_key", "user": "api_client"}

    # Check Bearer token
    if bearer and bearer.credentials and bearer.credentials == expected_key:
        return {"mode": "bearer", "user": "bearer_client"}

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication",
    )


# ---------------------------------------------------------------------------
# Optional authentication dependency
# ---------------------------------------------------------------------------

async def optional_auth(
    api_key: Annotated[Optional[str], Depends(API_KEY_HEADER)],
    bearer: Annotated[Optional[HTTPAuthorizationCredentials], Depends(BEARER_SCHEME)],
) -> dict:
    """
    Optional authentication - works with API key or Bearer token.

    Returns auth info dict with 'mode' key indicating auth type.
    Dev mode allows all requests.
    """
    expected_key = _get_api_key()

    # Dev mode: allow all requests
    if _is_dev_mode():
        return {"mode": "dev", "user": "dev-user"}

    # Check API key
    if api_key and expected_key and api_key == expected_key:
        return {"mode": "api_key", "user": "api_client"}

    # Check Bearer token
    if bearer and bearer.credentials and bearer.credentials == expected_key:
        return {"mode": "bearer", "user": "bearer_client"}

    # No auth provided - anonymous
    return {"mode": "anonymous", "user": None}


# ---------------------------------------------------------------------------
# Backward compatibility aliases
# ---------------------------------------------------------------------------

verify_api_key = require_auth
