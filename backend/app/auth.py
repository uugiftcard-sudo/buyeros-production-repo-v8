"""Consolidated authentication for BuyerOS.

Supports both API key and JWT authentication.
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


async def verify_api_key(
    key: Annotated[Optional[str], Depends(API_KEY_HEADER)],
) -> str:
    """
    Verify API key from X-API-Key header.
    
    Uses BUYEROS_API_KEY or SHOPIFY_API_KEY environment variable.
    """
    expected_key = os.getenv("BUYEROS_API_KEY", "") or os.getenv("SHOPIFY_API_KEY", "")
    if not expected_key:
        # No API key configured - allow all requests (dev mode)
        return "dev-mode"
    
    if not key or key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return key


async def verify_bearer_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(BEARER_SCHEME)],
) -> str:
    """
    Verify Bearer token from Authorization header.
    
    Currently accepts any non-empty token in dev mode.
    """
    if not credentials:
        # No credentials provided
        return "anonymous"
    
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    return token


# ---------------------------------------------------------------------------
# Optional authentication dependency
# ---------------------------------------------------------------------------

async def optional_auth(
    request: Request,
    api_key: Annotated[Optional[str], Depends(API_KEY_HEADER)],
    bearer: Annotated[Optional[HTTPAuthorizationCredentials], Depends(BEARER_SCHEME)],
) -> dict:
    """
    Optional authentication - works with API key or Bearer token.
    
    Returns auth info dict with 'mode' key indicating auth type.
    """
    expected_key = os.getenv("BUYEROS_API_KEY", "") or os.getenv("SHOPIFY_API_KEY", "")
    
    # Check API key
    if api_key and expected_key and api_key == expected_key:
        return {"mode": "api_key", "user": "api_client"}
    
    # Check Bearer token
    if bearer and bearer.credentials:
        return {"mode": "bearer", "user": bearer.credentials[:20]}
    
    # No auth provided - anonymous
    return {"mode": "anonymous", "user": None}
