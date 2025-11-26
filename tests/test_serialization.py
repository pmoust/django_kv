"""
Tests for serialization functionality.
"""

import pytest
from django.test import override_settings
from django.core.cache import cache


@pytest.mark.django_db
class TestSerialization:
    """Tests for value serialization."""

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_json_serializable_types(self):
        """Test that JSON-serializable types use JSON."""
        # String
        cache.set("str", "test", timeout=60)
        assert cache.get("str") == "test"

        # Number
        cache.set("num", 42, timeout=60)
        assert cache.get("num") == 42

        # Dict
        cache.set("dict", {"key": "value"}, timeout=60)
        assert cache.get("dict") == {"key": "value"}

        # List
        cache.set("list", [1, 2, 3], timeout=60)
        assert cache.get("list") == [1, 2, 3]

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_pickle_required_types(self):
        """Test that non-JSON types use pickle."""
        # Set with datetime (requires pickle)
        from datetime import datetime

        now = datetime.now()
        cache.set("datetime", now, timeout=60)
        retrieved = cache.get("datetime")
        assert isinstance(retrieved, datetime)
        assert retrieved == now

        # Set with set (requires pickle)
        test_set = {1, 2, 3}
        cache.set("set", test_set, timeout=60)
        retrieved = cache.get("set")
        assert retrieved == test_set

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_nested_structures(self):
        """Test nested data structures."""
        nested = {"level1": {"level2": {"level3": [1, 2, {"deep": "value"}]}}}
        cache.set("nested", nested, timeout=60)
        retrieved = cache.get("nested")
        assert retrieved == nested
        assert retrieved["level1"]["level2"]["level3"][2]["deep"] == "value"
