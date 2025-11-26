"""
Tests for DiskCacheBackend.
"""

import pytest

pytest.importorskip("diskcache")

from django_kv.backends.disk import DiskCacheBackend  # noqa: E402


@pytest.mark.django_db
def test_disk_backend_basic(tmp_path):
    cache_dir = tmp_path / "disk-cache"
    backend = DiskCacheBackend(directory=str(cache_dir), collection="disk_cache")

    backend.set("disk_key", {"value": 42}, timeout=60)
    assert backend.get("disk_key") == {"value": 42}

    backend.delete("disk_key")
    assert backend.get("disk_key") is None


@pytest.mark.django_db
def test_disk_backend_persistence(tmp_path):
    cache_dir = tmp_path / "disk-cache"
    backend = DiskCacheBackend(directory=str(cache_dir))
    backend.set("persist", "value", timeout=60)

    # Recreate backend pointing to same directory, value should remain.
    backend2 = DiskCacheBackend(directory=str(cache_dir))
    assert backend2.get("persist") == "value"
