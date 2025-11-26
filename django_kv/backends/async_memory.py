"""
Async in-memory cache backend using py-key-value-aio MemoryStore.
"""

from django_kv.backends.async_base import AsyncKeyValueCacheBackend

from pathlib import Path
import sys


def _load_async_memory_store():
    """Load AsyncMemoryStore from py-key-value-aio, adding vendored paths if needed."""
    try:
        from key_value.aio.stores.memory import MemoryStore as _AsyncMemoryStore  # type: ignore

        return _AsyncMemoryStore
    except ImportError:
        repo_root = Path(__file__).resolve().parents[2]
        candidate_paths = [
            repo_root / "external" / "py-key-value" / "key-value" / "key-value-aio" / "src",
            repo_root / "external" / "py-key-value" / "key-value" / "key-value-shared" / "src",
        ]
        added = False
        for path in candidate_paths:
            if path.exists() and str(path) not in sys.path:
                sys.path.insert(0, str(path))
                added = True
        if added:
            from key_value.aio.stores.memory import MemoryStore as _AsyncMemoryStore  # type: ignore

            return _AsyncMemoryStore
        raise


try:
    AsyncMemoryStore = _load_async_memory_store()
except ImportError:
    AsyncMemoryStore = None  # type: ignore


class AsyncMemoryCacheBackend(AsyncKeyValueCacheBackend):
    """
    Django async cache backend using in-memory storage.

    This backend uses py-key-value-aio's MemoryStore, providing fast,
    ephemeral storage perfect for development and testing with async views.

    Configuration example:
        CACHES = {
            'async_default': {
                'BACKEND': 'django_kv.backends.async_memory.AsyncMemoryCacheBackend',
                'COLLECTION': 'django_cache',
            }
        }
    """

    def __init__(self, location=None, params=None, **options):
        """
        Initialize the async memory cache backend.

        Args:
            location: Cache location (unused, for Django compatibility)
            params: Dictionary of cache parameters from settings
            **options: Additional Django cache options
        """
        if AsyncMemoryStore is None:
            raise ImportError(
                "AsyncMemoryStore is not available. Install py-key-value-aio: "
                "pip install py-key-value-aio[memory]"
            )
        store = AsyncMemoryStore()
        collection = options.pop("collection", None)
        if collection is None and params:
            collection = params.get("COLLECTION", "django_cache")
        if collection is None:
            collection = "django_cache"
        super().__init__(
            location=location, params=params, key_value=store, collection=collection, **options
        )
