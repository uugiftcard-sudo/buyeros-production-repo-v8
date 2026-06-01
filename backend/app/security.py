"""BuyerOS API key dependency (deprecated).

Use app.auth instead for consolidated authentication.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

from app.auth import require_auth, optional_auth

# For backward compatibility, re-export
__all__ = ["require_api_key", "verify_api_key"]


async def require_api_key(request: Request) -> None:
    """
    Verify API key from request headers.

    DEPRECATED: Use app.auth.require_auth instead.
    This function delegates to the new auth module.
    """
    # Extract headers manually since we don't have FastAPI dependencies here
    expected = os.getenv("BUYEROS_API_KEY", "").strip()
    
    if os.getenv("BUYEROS_DEV_MODE", "").lower() in ("true", "1", "yes"):
        return  # Dev mode
    
    if not expected:
        raise HTTPException(status_code=500, detail="BUYEROS_API_KEY not configured")
    
    bearer = request.headers.get("authorization", "")
    supplied = ""
    if bearer.lower().startswith("bearer "):
        supplied = bearer[7:].strip()
    else:
        supplied = request.headers.get("x-buyeros-api-key", "").strip()
    
    if supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
