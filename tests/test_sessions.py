"""
Integration tests for django-kv session backend.
"""

import pytest
from django.test import override_settings

from django_kv.sessions import SessionStore

MEMORY_CACHE = {
    "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
    "COLLECTION": "sessions",
}


@pytest.mark.django_db
@override_settings(
    DJANGO_KV_SESSION_CACHE_ALIAS="memory_sessions",
    CACHES={
        "default": MEMORY_CACHE,
        "memory_sessions": MEMORY_CACHE,
    },
)
def test_session_round_trip() -> None:
    store = SessionStore()
    store["user_id"] = 123
    store.save()

    key = store.session_key
    restored = SessionStore(session_key=key)
    assert restored["user_id"] == 123


@pytest.mark.django_db
@override_settings(
    # Exercise default alias fallback (django_kv_sessions)
    CACHES={
        "default": MEMORY_CACHE,
        "django_kv_sessions": MEMORY_CACHE,
    },
)
def test_session_default_alias() -> None:
    store = SessionStore()
    store["foo"] = "bar"
    store.save()

    restored = SessionStore(session_key=store.session_key)
    assert restored["foo"] == "bar"
