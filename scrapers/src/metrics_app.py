"""
Prometheus metrics ASGI app — mounts at /metrics.

Usage:
    from src.metrics_app import app as metrics_app
    app.mount("/metrics", metrics_app)
"""

from __future__ import annotations

from prometheus_client import make_asgi_app

# Create the metrics ASGI app (this is a Starlette app, compatible with FastAPI)
metrics_app = make_asgi_app()
