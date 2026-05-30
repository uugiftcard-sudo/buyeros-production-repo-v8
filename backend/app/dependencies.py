"""
Shared FastAPI dependencies.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# ---------------------------------------------------------------------------
# API Key verification
# ---------------------------------------------------------------------------

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    key: Annotated[str | None, Security(API_KEY_HEADER)],
) -> str:
    """
    Verify the incoming X-API-Key header against the configured secret.

    Set SHOPIFY_API_KEY in your environment or .env file.
    If the key is missing or wrong, raise 401.
    """
    expected_key = os.getenv("SHOPIFY_API_KEY", "")

    if not expected_key:
        # In dev mode without a key configured, allow requests but log a warning
        import logging
        logging.getLogger(__name__).warning(
            "SHOPIFY_API_KEY not set — requests are unauthenticated!"
        )
        return "dev-mode-no-key"

    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return key
