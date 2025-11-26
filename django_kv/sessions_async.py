"""
Async Django session backend backed by django-kv async caches.
"""

from __future__ import annotations

from django.conf import settings  # type: ignore
from django.contrib.sessions.backends.base import SessionBase  # type: ignore
from django.contrib.sessions.backends.cache import (  # type: ignore
    KEY_PREFIX as DEFAULT_KEY_PREFIX,
)
from django.core.cache import caches  # type: ignore

from django_kv.observability import record_session_metrics, session_span


class AsyncSessionStore(SessionBase):
    """
    Async session backend that routes to a django-kv async cache alias.

    Configure with:

    ```
    SESSION_ENGINE = "django_kv.sessions_async"
    DJANGO_KV_SESSION_CACHE_ALIAS = "django_kv_sessions_async"  # optional
    ```

    The alias must exist in `CACHES` and point to a django-kv async cache backend
    (e.g., AsyncMemoryCacheBackend).
    """

    cache_key_prefix = DEFAULT_KEY_PREFIX
    setting_name = "DJANGO_KV_SESSION_CACHE_ALIAS"
    default_alias = "django_kv_sessions_async"

    def __init__(self, session_key: str | None = None) -> None:
        self._cache = caches[self._resolve_cache_alias()]
        SessionBase.__init__(self, session_key=session_key)

    def _resolve_cache_alias(self) -> str:
        alias = getattr(settings, self.setting_name, None)
        if alias:
            return alias
        return getattr(settings, "SESSION_CACHE_ALIAS", self.default_alias)

    async def aload(self):
        """Async load session data from cache."""
        with session_span("load", self.session_key):
            try:
                data = await self._cache.aget(self.cache_key)
                if data is None:
                    data = {}
                self._session_cache = data
            except Exception:
                record_session_metrics("load", False)
                raise
        record_session_metrics("load", True)
        return data

    async def asave(self, must_create: bool = False):
        """Async save session data to cache."""
        with session_span("save", self.session_key):
            try:
                if self.session_key is None:
                    return self.create()
                data = self._get_session(no_load=must_create)
                await self._cache.aset(self.cache_key, data, timeout=self.get_expiry_age())
                self._session_cache = data
            except Exception:
                record_session_metrics("save", False)
                raise
        record_session_metrics("save", True)

    async def adelete(self, session_key: str | None = None):
        """Async delete session from cache."""
        if session_key is None:
            session_key = self.session_key
        if session_key is None:
            return
        with session_span("delete", session_key):
            try:
                cache_key = self.cache_key_prefix + session_key
                await self._cache.adelete(cache_key)
            except Exception:
                record_session_metrics("delete", False)
                raise
        record_session_metrics("delete", True)

    async def aexists(self, session_key: str) -> bool:
        """Async check if session exists in cache."""
        with session_span("exists", session_key):
            try:
                cache_key = self.cache_key_prefix + session_key
                result = await self._cache.ahas_key(cache_key)
            except Exception:
                record_session_metrics("exists", False)
                return False
        record_session_metrics("exists", True)
        return result

    # Sync methods delegate to async
    def load(self):
        """Sync wrapper around aload."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aload())

    def save(self, must_create: bool = False):
        """Sync wrapper around asave."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.asave(must_create))

    def delete(self, session_key: str | None = None):
        """Sync wrapper around adelete."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.adelete(session_key))

    def exists(self, session_key: str) -> bool:
        """Sync wrapper around aexists."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aexists(session_key))

    @property
    def cache_key(self) -> str:
        """Generate cache key for this session."""
        return self.cache_key_prefix + self.session_key
