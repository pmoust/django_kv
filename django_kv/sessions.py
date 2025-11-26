"""
Custom Django session backend backed by django-kv caches.
"""

from __future__ import annotations

from django.conf import settings  # type: ignore
from django.contrib.sessions.backends.base import SessionBase  # type: ignore
from django.contrib.sessions.backends.cache import (  # type: ignore
    KEY_PREFIX as DEFAULT_KEY_PREFIX,
    SessionStore as CacheSessionStore,
)
from django.core.cache import caches  # type: ignore

from django_kv.observability import record_session_metrics, session_span


class SessionStore(CacheSessionStore):
    """
    Session backend that routes to a django-kv cache alias.

    Configure with:

    ```
    SESSION_ENGINE = "django_kv.sessions"
    DJANGO_KV_SESSION_CACHE_ALIAS = "django_kv_sessions"  # optional
    ```

    The alias must exist in `CACHES` and point to a django-kv cache backend
    (memory, redis, etc.).
    """

    cache_key_prefix = DEFAULT_KEY_PREFIX
    setting_name = "DJANGO_KV_SESSION_CACHE_ALIAS"
    default_alias = "django_kv_sessions"

    def __init__(self, session_key: str | None = None) -> None:
        self._cache = caches[self._resolve_cache_alias()]
        SessionBase.__init__(self, session_key=session_key)

    def _resolve_cache_alias(self) -> str:
        alias = getattr(settings, self.setting_name, None)
        if alias:
            return alias
        return getattr(settings, "SESSION_CACHE_ALIAS", self.default_alias)

    def load(self):
        with session_span("load", self.session_key):
            try:
                data = super().load()
            except Exception:
                record_session_metrics("load", False)
                raise
        record_session_metrics("load", True)
        return data

    def save(self, must_create: bool = False):
        with session_span("save", self.session_key):
            try:
                result = super().save(must_create=must_create)
            except Exception:
                record_session_metrics("save", False)
                raise
        record_session_metrics("save", True)
        return result

    def delete(self, session_key: str | None = None):
        with session_span("delete", session_key or self.session_key):
            try:
                result = super().delete(session_key=session_key)
            except Exception:
                record_session_metrics("delete", False)
                raise
        record_session_metrics("delete", True)
        return result

    def exists(self, session_key: str):
        with session_span("exists", session_key):
            try:
                result = super().exists(session_key)
            except Exception:
                record_session_metrics("exists", False)
                raise
        record_session_metrics("exists", True)
        return result
