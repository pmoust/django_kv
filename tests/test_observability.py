"""
Tests for OpenTelemetry instrumentation.
"""

import pytest
from django.test import override_settings

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from django_kv import observability
from django_kv.backends.memory import MemoryCacheBackend
from django_kv.sessions import SessionStore


@pytest.fixture(scope="module")
def _otel_exporter_module():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # OpenTelemetry does not allow overriding providers without clearing the global.
    if hasattr(trace, "_TRACER_PROVIDER"):
        trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace.set_tracer_provider(provider)
    yield exporter
    exporter.clear()
    if hasattr(trace, "_TRACER_PROVIDER"):
        trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]


@pytest.fixture()
def otel_exporter(_otel_exporter_module):
    _otel_exporter_module.clear()
    yield _otel_exporter_module


@pytest.mark.django_db
@override_settings(DJANGO_KV_OTEL={"ENABLED": True, "METRICS_ENABLED": False})
def test_cache_spans_emitted(otel_exporter):
    observability.reload_config()
    backend = MemoryCacheBackend(collection="otel_cache")
    backend.set("otel:key", "value", timeout=30)
    backend.get("otel:key")

    names = [span.name for span in otel_exporter.get_finished_spans()]
    assert "django_kv.cache.set" in names
    assert "django_kv.cache.get" in names


@pytest.mark.django_db
@override_settings(DJANGO_KV_OTEL={"ENABLED": True, "METRICS_ENABLED": False})
def test_session_spans_emitted(otel_exporter):
    observability.reload_config()
    store = SessionStore()
    store["user"] = "alice"
    store.save()

    reloaded = SessionStore(session_key=store.session_key)
    reloaded.load()

    names = [span.name for span in otel_exporter.get_finished_spans()]
    assert "django_kv.session.save" in names
    assert "django_kv.session.load" in names


@override_settings(DJANGO_KV_OTEL={"ENABLED": True, "AUTO_INSTRUMENT_DJANGO": True})
def test_auto_instrument_django(monkeypatch):
    observability.reload_config()

    called = {"count": 0}

    class FakeInstrumentor:
        def instrument(self):
            called["count"] += 1

    monkeypatch.setattr(observability, "DjangoInstrumentor", FakeInstrumentor)
    assert observability.auto_instrument_django() is True
    assert called["count"] == 1
    # second call should be no-op
    assert observability.auto_instrument_django() is False
    assert called["count"] == 1
