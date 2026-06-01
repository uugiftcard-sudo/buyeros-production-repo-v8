"""Prometheus metrics for BuyerOS."""

from __future__ import annotations

import time
from typing import Callable
from functools import wraps

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


# Request metrics
REQUEST_COUNT = Counter(
    "buyeros_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "buyeros_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Business metrics
TASKS_CREATED = Counter(
    "buyeros_tasks_created_total",
    "Total tasks created",
)

TASKS_COMPLETED = Counter(
    "buyeros_tasks_completed_total",
    "Total tasks completed",
)

MEMORY_OPERATIONS = Counter(
    "buyeros_memory_operations_total",
    "Memory store operations",
    ["operation"],
)

ACTIVE_TASKS = Gauge(
    "buyeros_active_tasks",
    "Number of active tasks",
)

# Error metrics
ERROR_COUNT = Counter(
    "buyeros_errors_total",
    "Total errors",
    ["type", "endpoint"],
)


def track_request_metrics(request: Request, call_next: Callable) -> Response:
    """Middleware to track request metrics."""
    start_time = time.time()
    
    response = call_next(request)
    
    # Track request count and latency
    endpoint = request.url.path
    method = request.method
    status = response.status_code
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    
    duration = time.time() - start_time
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response


def track_error(error_type: str, endpoint: str) -> None:
    """Track an error."""
    ERROR_COUNT.labels(type=error_type, endpoint=endpoint).inc()


def track_task_created() -> None:
    """Track task creation."""
    TASKS_CREATED.inc()


def track_task_completed() -> None:
    """Track task completion."""
    TASKS_COMPLETED.inc()
    ACTIVE_TASKS.dec()


def track_memory_operation(operation: str) -> None:
    """Track memory operation."""
    MEMORY_OPERATIONS.labels(operation=operation).inc()
