"""OpenTelemetry tracing configuration for BuyerOS."""

from __future__ import annotations

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Tracer


_tracer: Optional[Tracer] = None


def setup_tracing(service_name: str = "buyeros-backend") -> Tracer:
    """Setup OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service for tracing
        
    Returns:
        Configured tracer instance
    """
    global _tracer
    
    # Create resource
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": os.getenv("APP_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create provider
    provider = TracerProvider(resource=resource)
    
    # Add console exporter for development
    if os.getenv("OTEL_TRACE_CONSOLE", "") == "true":
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
    
    # Add OTLP exporter if configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            provider.add_span_processor(processor)
        except ImportError:
            pass
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    
    return _tracer


def get_tracer() -> Tracer:
    """Get the configured tracer.
    
    Returns:
        Tracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = setup_tracing()
    return _tracer


class TracingMiddleware:
    """Middleware for adding tracing context to requests."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        tracer = get_tracer()
        request_id = scope.get("headers", {}).get("x-request-id", b"unknown").decode()
        
        with tracer.start_as_current_span(
            f"{scope['method']} {scope['path']}",
            attributes={
                "http.method": scope["method"],
                "http.url": scope["path"],
                "http.request_id": request_id,
            },
        ) as span:
            await self.app(scope, receive, send)
