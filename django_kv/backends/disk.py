"""
Disk-backed cache using py-key-value DiskStore.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django_kv.backends.base import KeyValueCacheBackend


def _load_disk_store():
    try:
        from key_value.sync.stores.disk import DiskStore as _DiskStore

        return _DiskStore
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
            from key_value.sync.stores.disk import DiskStore as _DiskStore  # type: ignore

            return _DiskStore
        raise


DiskStore = None


def _ensure_disk_store():
    global DiskStore
    if DiskStore is not None:
        return DiskStore
    DiskStore = _load_disk_store()
    return DiskStore


class DiskCacheBackend(KeyValueCacheBackend):
    """
    Disk-backed cache using diskcache via py-key-value DiskStore.
    """

    def __init__(self, location=None, params=None, **options):
        try:
            store_cls = _ensure_disk_store()
        except ImportError as exc:
            raise ImportError(
                "DiskStore is not available. Install py-key-value with disk support: "
                "pip install py-key-value[disk]"
            ) from exc
        params = params or {}

        directory = (
            options.pop("directory", None)
            or params.get("DIRECTORY")
            or params.get("LOCATION")
            or location
        )
        if directory is None:
            raise ValueError("DIRECTORY (or LOCATION) must be provided for DiskCacheBackend")

        max_size = options.pop("max_size", None) or params.get("MAX_SIZE")
        collection = options.pop("collection", None) or params.get("COLLECTION") or "django_cache"

        path = Path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)

        store = store_cls(directory=str(path), max_size=max_size, default_collection=collection)
        super().__init__(
            location=location, params=params, key_value=store, collection=collection, **options
        )
