"""
Structured logging setup with optional Rich formatting.

All modules import `log` from this module for consistent log formatting.
"""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

from src.config import get_log_level

# ─── Rich console (shared across logging + CLI) ──────────────────
_console = Console(stderr=True)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure the root logger with Rich handler.

    Returns the root logger. Child loggers (e.g. `log = logging.getLogger(__name__)`)
    inherit this configuration automatically.
    """
    level = logging.DEBUG if verbose else getattr(logging, get_log_level().upper(), logging.INFO)

    # Remove any existing handlers to avoid duplication on re-init
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)

    rich_handler = RichHandler(
        console=_console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True,
    )
    rich_handler.setLevel(level)

    # Root logger config
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler],
    )

    # Silence noisy third-party loggers
    for _logger in ("httpx", "urllib3", "requests"):
        logging.getLogger(_logger).setLevel(logging.WARNING)

    return logging.getLogger("scrapers")


# ─── Module-level logger (used by all submodules) ───────────────
def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger for the given name (or the scrapers root logger)."""
    if name:
        return logging.getLogger(f"scrapers.{name}")
    return logging.getLogger("scrapers")
