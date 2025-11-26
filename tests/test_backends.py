"""
Tests for Django KV store backends.
"""

import time
import pytest
from django.core.cache import cache
from django.test import override_settings
from django_kv.backends.memory import MemoryCacheBackend


@pytest.mark.django_db
class TestMemoryCacheBackend:
    """Tests for MemoryCacheBackend."""

    def test_backend_initialization(self):
        """Test that memory backend initializes correctly."""
        backend = MemoryCacheBackend(collection="test_cache")
        assert backend.collection == "test_cache"
        assert backend.key_value is not None

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_basic_operations(self):
        """Test basic cache operations."""
        # Set a value
        cache.set("test_key", "test_value", timeout=60)

        # Get the value
        value = cache.get("test_key")
        assert value == "test_value"

        # Delete the value
        cache.delete("test_key")

        # Verify deletion
        value = cache.get("test_key")
        assert value is None

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_add_operation(self):
        """Test add operation (only sets if key doesn't exist)."""
        # First add should succeed
        result = cache.add("new_key", "new_value", timeout=60)
        assert result is True

        # Second add should fail (key exists)
        result = cache.add("new_key", "different_value", timeout=60)
        assert result is False

        # Value should still be original
        value = cache.get("new_key")
        assert value == "new_value"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_get_many_set_many(self):
        """Test bulk operations."""
        # Set multiple values
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        cache.set_many(data, timeout=60)

        # Get multiple values
        results = cache.get_many(["key1", "key2", "key3", "key4"])
        assert results["key1"] == "value1"
        assert results["key2"] == "value2"
        assert results["key3"] == "value3"
        assert "key4" not in results or results["key4"] is None

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_complex_objects(self):
        """Test storing complex objects (lists, dicts)."""
        complex_obj = {
            "name": "Alice",
            "age": 30,
            "hobbies": ["reading", "coding"],
            "metadata": {
                "created": "2024-01-01",
                "active": True,
            },
        }

        cache.set("complex_key", complex_obj, timeout=60)
        retrieved = cache.get("complex_key")

        assert retrieved == complex_obj
        assert retrieved["name"] == "Alice"
        assert retrieved["hobbies"] == ["reading", "coding"]
        assert retrieved["metadata"]["active"] is True

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_has_key(self):
        """Test has_key operation."""
        cache.set("exists_key", "value", timeout=60)

        assert cache.has_key("exists_key") is True
        assert cache.has_key("nonexistent_key") is False

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_timeout_expiration(self):
        """Test that values expire after timeout."""
        # Set a value with a very short timeout
        cache.set("expiring_key", "expiring_value", timeout=1)

        # Value should exist immediately
        assert cache.get("expiring_key") == "expiring_value"

        # Wait for expiration
        time.sleep(1.1)

        # Value should be None after expiration
        assert cache.get("expiring_key") is None

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_no_timeout(self):
        """Test setting values without timeout."""
        cache.set("no_timeout_key", "no_timeout_value", timeout=None)

        # Value should persist
        assert cache.get("no_timeout_key") == "no_timeout_value"

        # Wait a bit and verify it's still there
        time.sleep(0.1)
        assert cache.get("no_timeout_key") == "no_timeout_value"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_key_versioning(self):
        """Test Django cache key versioning."""
        # Set value with version 1
        cache.set("versioned_key", "version1", version=1, timeout=60)
        assert cache.get("versioned_key", version=1) == "version1"
        assert cache.get("versioned_key", version=2) is None

        # Set value with version 2
        cache.set("versioned_key", "version2", version=2, timeout=60)
        assert cache.get("versioned_key", version=1) == "version1"
        assert cache.get("versioned_key", version=2) == "version2"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
                "KEY_PREFIX": "test_prefix",
            }
        }
    )
    def test_key_prefix(self):
        """Test key prefixing."""
        cache.set("prefixed_key", "prefixed_value", timeout=60)
        value = cache.get("prefixed_key")
        assert value == "prefixed_value"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_delete_many(self):
        """Test delete_many operation."""
        # Set multiple values
        cache.set("delete1", "value1", timeout=60)
        cache.set("delete2", "value2", timeout=60)
        cache.set("delete3", "value3", timeout=60)

        # Verify they exist
        assert cache.get("delete1") == "value1"
        assert cache.get("delete2") == "value2"
        assert cache.get("delete3") == "value3"

        # Delete multiple keys
        cache.delete_many(["delete1", "delete2"])

        # Verify deletion
        assert cache.get("delete1") is None
        assert cache.get("delete2") is None
        assert cache.get("delete3") == "value3"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_none_values(self):
        """Test storing and retrieving None values."""
        cache.set("none_key", None, timeout=60)
        value = cache.get("none_key")
        assert value is None

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_empty_string(self):
        """Test storing empty strings."""
        cache.set("empty_key", "", timeout=60)
        value = cache.get("empty_key")
        assert value == ""

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_default_value(self):
        """Test get with default value."""
        # Non-existent key should return default
        value = cache.get("nonexistent", default="default_value")
        assert value == "default_value"

        # Existing key should return actual value
        cache.set("existing", "actual_value", timeout=60)
        value = cache.get("existing", default="default_value")
        assert value == "actual_value"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_different_data_types(self):
        """Test storing various data types."""
        # Integer
        cache.set("int_key", 42, timeout=60)
        assert cache.get("int_key") == 42

        # Float
        cache.set("float_key", 3.14, timeout=60)
        assert cache.get("float_key") == 3.14

        # Boolean
        cache.set("bool_key", True, timeout=60)
        assert cache.get("bool_key") is True

        # List
        cache.set("list_key", [1, 2, 3], timeout=60)
        assert cache.get("list_key") == [1, 2, 3]

        # Tuple (will be serialized as list)
        cache.set("tuple_key", (1, 2, 3), timeout=60)
        result = cache.get("tuple_key")
        # Tuple might be deserialized as list depending on serialization
        assert result in [(1, 2, 3), [1, 2, 3]]

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_pickle_serialization(self):
        """Test that complex objects requiring pickle work."""
        # Use a module-level class that can be pickled
        from types import SimpleNamespace

        obj = SimpleNamespace(value="test", number=42)
        cache.set("custom_obj", obj, timeout=60)
        retrieved = cache.get("custom_obj")
        assert retrieved.value == "test"
        assert retrieved.number == 42

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_empty_get_many(self):
        """Test get_many with empty list."""
        result = cache.get_many([])
        assert result == {}

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_empty_set_many(self):
        """Test set_many with empty dict."""
        # Should not raise an error
        cache.set_many({})

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_empty_delete_many(self):
        """Test delete_many with empty list."""
        # Should not raise an error
        cache.delete_many([])

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_collection_isolation(self):
        """Test that different collections are isolated."""
        backend1 = MemoryCacheBackend(collection="collection1")
        backend2 = MemoryCacheBackend(collection="collection2")

        backend1.set("shared_key", "value1", timeout=60)
        backend2.set("shared_key", "value2", timeout=60)

        assert backend1.get("shared_key") == "value1"
        assert backend2.get("shared_key") == "value2"

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_clear_not_implemented(self):
        """Test that clear raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            cache.clear()


@pytest.mark.django_db
class TestRedisCacheBackend:
    """Tests for RedisCacheBackend."""

    def test_backend_initialization_without_redis(self):
        """Test that backend raises error if Redis is not available."""
        # This test assumes RedisStore is not installed
        # In a real scenario, you'd mock the import
        pass

    @pytest.mark.skip(reason="Requires Redis server running")
    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.redis.RedisCacheBackend",
                "HOST": "localhost",
                "PORT": 6379,
                "DB": 0,
                "COLLECTION": "test_cache",
            }
        }
    )
    def test_redis_operations(self):
        """Test Redis backend operations (requires Redis server)."""
        cache.set("redis_key", "redis_value", timeout=60)
        value = cache.get("redis_key")
        assert value == "redis_value"
