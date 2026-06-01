"""Request trace context shared by BuyerOS agents."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Optional


_trace_ctx: ContextVar[dict[str, Any]] = ContextVar("buyeros_trace_ctx", default={})


def set_trace(
    *,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> None:
    _trace_ctx.set(
        {
            "request_id": request_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "client_ip": client_ip,
        }
    )


def clear_trace() -> None:
    _trace_ctx.set({})


def trace_ctx() -> dict[str, Any]:
    return dict(_trace_ctx.get() or {})
