"""
Tests for Django KV store utilities.
"""

from django.test import override_settings
from django_kv.utils import get_kv_store, get_kv_store_config


class TestUtils:
    """Tests for utility functions."""

    def test_get_kv_store_config_no_config(self):
        """Test get_kv_store_config when KV_STORE is not configured."""
        with override_settings(KV_STORE=None):
            config = get_kv_store_config()
            assert config is None

    def test_get_kv_store_config_with_config(self):
        """Test get_kv_store_config when KV_STORE is configured."""
        test_config = {
            "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
            "COLLECTION": "test_store",
        }
        with override_settings(KV_STORE=test_config):
            config = get_kv_store_config()
            assert config == test_config

    def test_get_kv_store_no_config(self):
        """Test get_kv_store when KV_STORE is not configured."""
        with override_settings(KV_STORE=None):
            store = get_kv_store()
            assert store is None

    def test_get_kv_store_with_config(self):
        """Test get_kv_store when KV_STORE is configured."""
        test_config = {
            "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
            "COLLECTION": "test_store",
        }
        with override_settings(KV_STORE=test_config):
            store = get_kv_store()
            assert store is not None
            # Verify it's a KeyValue store
            assert hasattr(store, "get")
            assert hasattr(store, "put")
            assert hasattr(store, "delete")

    def test_get_kv_store_with_options(self):
        """Test get_kv_store with OPTIONS dict."""
        test_config = {
            "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
            "COLLECTION": "test_store",
            "OPTIONS": {
                "KEY_PREFIX": "test_prefix",
            },
        }
        with override_settings(KV_STORE=test_config):
            store = get_kv_store()
            assert store is not None

    def test_get_kv_store_direct_usage(self):
        """Test using the KV store directly."""
        test_config = {
            "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
            "COLLECTION": "test_store",
        }
        with override_settings(KV_STORE=test_config):
            store = get_kv_store()
            assert store is not None

            # Use the store directly
            store.put(key="direct_key", value={"data": "value"}, collection="test_collection")
            result = store.get(key="direct_key", collection="test_collection")
            assert result == {"data": "value"}
