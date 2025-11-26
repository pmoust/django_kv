"""
Async-first helpers for django-kv using py-key-value-aio.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings  # type: ignore

try:
    from key_value.aio.protocols.key_value import AsyncKeyValue
    from key_value.aio.stores.memory import MemoryStore as AsyncMemoryStore
except ImportError:  # pragma: no cover - optional dependency
    AsyncKeyValue = Any  # type: ignore
    AsyncMemoryStore = None  # type: ignore


ASYNC_DEFAULT_CONFIG: Dict[str, Any] = {
    "BACKEND": "memory",
    "OPTIONS": {},
}


def get_async_kv_store_config() -> Dict[str, Any]:
    """
    Retrieve async KV store configuration from Django settings.

    Example:
        ASYNC_KV_STORE = {
            "BACKEND": "memory",  # future: redis, disk, etc.
            "OPTIONS": {},
        }
    """
    return getattr(settings, "ASYNC_KV_STORE", ASYNC_DEFAULT_CONFIG)


async def get_async_kv_store() -> Optional[AsyncKeyValue]:
    """
    Create an AsyncKeyValue instance based on settings.

    Currently supports:
      - BACKEND='memory' using py-key-value-aio MemoryStore
    """
    if AsyncMemoryStore is None:
        return None
    cfg = get_async_kv_store_config()
    backend = cfg.get("BACKEND", "memory")
    options = cfg.get("OPTIONS", {}) or {}

    if backend == "memory":
        return AsyncMemoryStore(**options)

    # Future: add redis/disk/others here
    raise ValueError(f"Unsupported async backend: {backend!r}")
