"""
In-memory cache backend using py-key-value MemoryStore.

Perfect for development and CI environments.
"""

from django_kv.backends.base import KeyValueCacheBackend

from pathlib import Path
import sys


def _load_memory_store():
    """Load MemoryStore from py-key-value, adding vendored paths if needed."""
    try:
        from key_value.sync.stores.memory import MemoryStore as _MemoryStore  # type: ignore

        return _MemoryStore
    except ImportError:
        repo_root = Path(__file__).resolve().parents[2]
        candidate_paths = [
            repo_root / "external" / "py-key-value" / "key-value" / "key-value-sync" / "src",
            repo_root / "external" / "py-key-value" / "key-value" / "key-value-shared" / "src",
        ]
        added = False
        for path in candidate_paths:
            if path.exists() and str(path) not in sys.path:
                sys.path.insert(0, str(path))
                added = True
        if added:
            from key_value.sync.stores.memory import MemoryStore as _MemoryStore  # type: ignore

            return _MemoryStore
        raise


try:
    MemoryStore = _load_memory_store()
except ImportError:
    MemoryStore = None  # type: ignore


class MemoryCacheBackend(KeyValueCacheBackend):
    """
    Django cache backend using in-memory storage.

    This backend uses py-key-value's MemoryStore, providing fast,
    ephemeral storage perfect for development and testing.

    Configuration example:
        CACHES = {
            'default': {
                'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
                'COLLECTION': 'django_cache',
            }
        }
    """

    def __init__(self, location=None, params=None, **options):
        """
        Initialize the memory cache backend.

        Args:
            location: Cache location (unused, for Django compatibility)
            params: Dictionary of cache parameters from settings
            **options: Additional Django cache options
        """
        if MemoryStore is None:
            raise ImportError(
                "MemoryStore is not available. Install py-key-value: " "pip install py-key-value"
            )
        store = MemoryStore()
        # Extract collection from params or options
        collection = options.pop("collection", None)
        if collection is None and params:
            collection = params.get("COLLECTION", "django_cache")
        if collection is None:
            collection = "django_cache"
        super().__init__(
            location=location, params=params, key_value=store, collection=collection, **options
        )
