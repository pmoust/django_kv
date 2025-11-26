"""
OpenTelemetry helpers for django-kv.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Optional

from django.conf import settings  # type: ignore

logger = logging.getLogger(__name__)

try:
    from opentelemetry import metrics, trace
    from opentelemetry.trace import StatusCode
    from opentelemetry.instrumentation.django import DjangoInstrumentor
except ImportError:  # pragma: no cover
    metrics = None  # type: ignore
    trace = None  # type: ignore
    StatusCode = None  # type: ignore
    DjangoInstrumentor = None  # type: ignore


DEFAULT_CONFIG: Dict[str, Any] = {
    "ENABLED": False,
    "INSTRUMENT_CACHE": True,
    "INSTRUMENT_SESSIONS": True,
    "METRICS_ENABLED": True,
    "AUTO_INSTRUMENT_DJANGO": False,
}

_config: Optional[Dict[str, Any]] = None
_tracer = None
_meter = None
_missing_warning_logged = False
_request_counter = None
_hit_counter = None
_miss_counter = None
_error_counter = None
_session_counter = None
_django_instrumented = False


def _load_config() -> Dict[str, Any]:
    global _config
    if _config is not None:
        return _config
    user_cfg = getattr(settings, "DJANGO_KV_OTEL", None) or {}
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(user_cfg)
    _config = cfg
    return _config


def reload_config() -> None:
    global _config, _tracer, _meter, _request_counter, _hit_counter, _miss_counter, _error_counter, _session_counter, _missing_warning_logged, _django_instrumented
    _config = None
    _tracer = None
    _meter = None
    _request_counter = None
    _hit_counter = None
    _miss_counter = None
    _error_counter = None
    _session_counter = None
    _missing_warning_logged = False
    _django_instrumented = False


def _enabled(key: str) -> bool:
    cfg = _load_config()
    if not cfg.get("ENABLED"):
        return False
    global _missing_warning_logged
    if trace is None and metrics is None:
        if not _missing_warning_logged:
            logger.warning("DJANGO_KV_OTEL is enabled but OpenTelemetry packages are not installed")
            _missing_warning_logged = True
        return False
    return cfg.get(key, True)


def _get_tracer():
    global _tracer
    if trace is None:
        return None
    if _tracer is None:
        _tracer = trace.get_tracer("django-kv")
    return _tracer


def _get_meter():
    global _meter
    if metrics is None:
        return None
    if _meter is None:
        _meter = metrics.get_meter("django-kv")
    return _meter


@contextmanager
def cache_span(
    operation: str,
    backend: str,
    collection: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    if not _enabled("INSTRUMENT_CACHE"):
        yield None
        return
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    name = f"django_kv.cache.{operation}"
    base_attrs = {
        "django_kv.cache.backend": backend,
    }
    if collection:
        base_attrs["django_kv.cache.collection"] = collection
    with tracer.start_as_current_span(name) as span:
        for key, value in base_attrs.items():
            span.set_attribute(key, value)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:  # pragma: no cover - handled via tests
            if StatusCode:
                span.set_status(StatusCode.ERROR)  # type: ignore[attr-defined]
            span.record_exception(exc)
            raise


def record_cache_metrics(
    operation: str,
    backend: str,
    hit: Optional[bool] = None,
    hit_count: Optional[int] = None,
    miss_count: Optional[int] = None,
    error: bool = False,
):
    if not (_enabled("METRICS_ENABLED") and metrics is not None):
        return
    meter = _get_meter()
    if meter is None:
        return
    global _request_counter, _hit_counter, _miss_counter, _error_counter
    if _request_counter is None:
        _request_counter = meter.create_counter(
            "django_kv.cache.requests", description="Total cache operations"
        )
        _hit_counter = meter.create_counter("django_kv.cache.hits", description="Cache hits")
        _miss_counter = meter.create_counter("django_kv.cache.misses", description="Cache misses")
        _error_counter = meter.create_counter("django_kv.cache.errors", description="Cache errors")
    attrs = {"django_kv.cache.backend": backend, "django_kv.cache.operation": operation}
    _request_counter.add(1, attributes=attrs)
    if error:
        _error_counter.add(1, attributes=attrs)
    if hit is True:
        _hit_counter.add(1, attributes=attrs)
    elif hit is False:
        _miss_counter.add(1, attributes=attrs)
    if hit_count is not None and hit_count > 0:
        _hit_counter.add(hit_count, attributes=attrs)
    if miss_count is not None and miss_count > 0:
        _miss_counter.add(miss_count, attributes=attrs)


@contextmanager
def session_span(operation: str, session_key: Optional[str] = None):
    if not _enabled("INSTRUMENT_SESSIONS"):
        yield None
        return
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    name = f"django_kv.session.{operation}"
    with tracer.start_as_current_span(name) as span:
        if session_key:
            span.set_attribute("django_kv.session.key", session_key)
        try:
            yield span
        except Exception as exc:  # pragma: no cover
            if StatusCode:
                span.set_status(StatusCode.ERROR)  # type: ignore[attr-defined]
            span.record_exception(exc)
            raise


def record_session_metrics(operation: str, success: bool):
    if not (_enabled("METRICS_ENABLED") and metrics is not None):
        return
    meter = _get_meter()
    if meter is None:
        return
    global _session_counter
    if _session_counter is None:
        _session_counter = meter.create_counter(
            "django_kv.session.operations", description="Session backend operations"
        )
    attrs = {"django_kv.session.operation": operation, "django_kv.session.success": success}
    _session_counter.add(1, attributes=attrs)


def auto_instrument_django() -> bool:
    """
    Automatically instrument Django via opentelemetry instrumentation if enabled.
    """
    cfg = _load_config()
    if not (cfg.get("ENABLED") and cfg.get("AUTO_INSTRUMENT_DJANGO")):
        return False
    if DjangoInstrumentor is None:  # pragma: no cover - requires extra package
        logger.warning(
            "AUTO_INSTRUMENT_DJANGO enabled but opentelemetry-instrumentation-django not installed"
        )
        return False
    global _django_instrumented
    if _django_instrumented:
        return False
    DjangoInstrumentor().instrument()
    _django_instrumented = True
    return True
