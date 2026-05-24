"""Lightweight distributed tracing via contextvars.

Provides request-level trace context (request_id, trace_id, span_id) that
flows automatically through async call chains without an external collector.

Usage:
    from .trace import trace_ctx, set_trace, clear_trace

    # At request entry (in middleware or endpoint):
    set_trace(request_id=req_id, trace_id=trace_id, span_id=span_id)

    # Anywhere in the call chain (agents, tools, services):
    ctx = trace_ctx()   # returns {request_id, trace_id, span_id, ...}

    # At request exit:
    clear_trace()
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Global trace context — thread/async-safe
_trace: ContextVar[Optional[Dict[str, Any]]] = ContextVar("_trace", default=None)


def trace_ctx() -> Dict[str, Any]:
    """Return current trace context (never raises, never None)."""
    return _trace.get() or {}


def set_trace(
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """Set or merge fields into the current trace context."""
    ctx = _trace.get() or {}
    if request_id is not None:
        ctx["request_id"] = request_id
    if trace_id is not None:
        ctx["trace_id"] = trace_id
    if span_id is not None:
        ctx["span_id"] = span_id
    if extra:
        ctx.update(extra)
    _trace.set(ctx)


def clear_trace() -> None:
    """Clear the trace context (call at request boundary)."""
    _trace.set(None)


def new_trace_id() -> str:
    """Generate a new trace ID (16 hex chars, i.e. 64-bit)."""
    return uuid.uuid4().hex[:16]


def new_span_id() -> str:
    """Generate a new span ID (8 hex chars, i.e. 32-bit)."""
    return uuid.uuid4().hex[:8]
