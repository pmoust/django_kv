"""
Helper utilities to bootstrap OpenTelemetry providers for django-kv.
"""

from __future__ import annotations

from typing import Dict, Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
except ImportError:  # pragma: no cover
    trace = None  # type: ignore
    TracerProvider = None  # type: ignore


def init_tracing(
    service_name: str = "django-kv",
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
):
    """
    Initialize a basic OTLP trace pipeline.

    Args:
        service_name: Value for ``service.name`` resource attribute.
        endpoint: OTLP endpoint (grpc). Defaults to ``OTEL_EXPORTER_OTLP_ENDPOINT``.
        headers: Optional headers to send to collector.
    """
    if trace is None or TracerProvider is None:
        raise ImportError("opentelemetry-sdk and otlp exporter are required for init_tracing")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider
