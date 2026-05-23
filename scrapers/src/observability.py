"""
Observability bootstrap — structured logging + Sentry error tracking.

Import this at app startup (e.g. in src/__init__.py or the API lifespan)
to activate structured logging and optional Sentry tracing.

Usage:
    from src.observability import setup_observability
    setup_observability()
"""

from __future__ import annotations

import logging
import os
import sys

__all__ = ["setup_observability"]


def setup_observability() -> None:
    """
    Configure structlog + optional Sentry for the current process.

    Call once at application startup.
    """
    _setup_structlog()
    _setup_sentry()


def _setup_structlog() -> None:
    """
    Configure structlog for structured JSON output in production
    and pretty colour output in development.
    """
    try:
        import structlog
    except ImportError:
        return  # pro extras not installed — fall back to stdlib

    log_format = os.getenv("LOG_FORMAT", "text")
    is_production = log_format == "json"

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect stdlib root logger to use structlog processors
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    )


def _setup_sentry() -> None:
    """Initialise Sentry if SENTRY_DSN is set in the environment."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk  # type: ignore[import]
    except ImportError:
        logging.warning("[observability] SENTRY_DSN is set but sentry-sdk is not installed")
        return

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("RELEASE", None),
        _experiments={
            "max_spans": 1000,
        },
    )
    logging.info("[observability] Sentry initialised")
