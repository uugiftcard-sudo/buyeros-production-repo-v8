"""Structured logging configuration for BuyerOS."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    include_caller: bool = True,
) -> None:
    """Configure logging for BuyerOS.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output logs as JSON
        include_caller: If True, include caller info
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        format_str = (
            "%(asctime)s %(levelname)s %(name)s:%(lineno)d — %(message)s"
            if include_caller
            else "%(asctime)s %(levelname)s %(name)s — %(message)s"
        )
        handler.setFormatter(logging.Formatter(format_str))

    root_logger.addHandler(handler)


def get_logger(name: str, **kwargs: Any) -> logging.Logger:
    """Get a logger with extra fields.

    Args:
        name: Logger name (typically __name__)
        **kwargs: Extra fields to include in every log message

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if kwargs:
        old_log = logger.log
        def log_with_extra(level: int, msg: str, *args: Any, **log_kwargs: Any) -> None:
            log_kwargs["extra"] = {**kwargs, **log_kwargs.get("extra", {})}
            old_log(level, msg, *args, **log_kwargs)
        logger.log = log_with_extra  # type: ignore
    return logger
