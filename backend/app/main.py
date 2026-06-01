"""
FastAPI main application entry point.

Runs on http://0.0.0.0:8000
API docs: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routers import shopify_router
from app.routers import tiktok_router
from app.routers import api_router
from app.routers import metrics_router
from app.rate_limit import limiter, rate_limit_exceeded_handler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting BuyerOS Backend API")
    # Log only configured status, not the actual key
    shopify_key = os.getenv("SHOPIFY_API_KEY", "")
    logger.info("Shopify connector: %s", "configured" if shopify_key else "mock mode")
    yield
    logger.info("Shutting down BuyerOS Backend API")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="BuyerOS Backend API",
        description="Backend API for CLOTH/BuyerOS luxury resale platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # CORS — allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "https://buyeros.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(shopify_router)
    app.include_router(tiktok_router)
    app.include_router(api_router)
    app.include_router(metrics_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    return app


# ---------------------------------------------------------------------------
# Run directly (uvicorn)
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
