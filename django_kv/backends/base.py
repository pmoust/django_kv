"""
Base backend class for Django cache integration with py-key-value stores.
"""

import pickle
import json
from typing import Any, Optional, Dict, List, TYPE_CHECKING

try:
    from key_value.sync.protocols.key_value import KeyValue
except ImportError:
    # For type checking when py-key-value is not installed
    if TYPE_CHECKING:
        from typing import Protocol

        class KeyValue(Protocol):
            def get(
                self, key: str, collection: Optional[str] = None
            ) -> Optional[Dict[str, Any]]: ...

            def put(
                self,
                key: str,
                value: Dict[str, Any],
                collection: Optional[str] = None,
                ttl: Optional[float] = None,
            ) -> None: ...
            def delete(self, key: str, collection: Optional[str] = None) -> bool: ...

            def get_many(
                self, keys: List[str], collection: Optional[str] = None
            ) -> List[Optional[Dict[str, Any]]]: ...

            def put_many(
                self,
                keys: List[str],
                values: List[Dict[str, Any]],
                collection: Optional[str] = None,
                ttl: Optional[float] = None,
            ) -> None: ...
            def delete_many(self, keys: List[str], collection: Optional[str] = None) -> int: ...

    else:
        KeyValue = Any  # type: ignore

from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.utils.encoding import force_str

from django_kv.observability import cache_span, record_cache_metrics


class KeyValueCacheBackend(BaseCache):
    """
    Base class for Django cache backends using py-key-value stores.

    This class bridges Django's cache framework with py-key-value stores,
    handling serialization, key versioning, and TTL management.
    """

    def __init__(
        self,
        location=None,
        params=None,
        key_value: Optional[KeyValue] = None,
        collection: Optional[str] = None,
        **options,
    ):
        """
        Initialize the cache backend.

        Args:
            location: Cache location (unused, for Django compatibility)
            params: Dictionary of cache parameters from settings
            key_value: A py-key-value KeyValue store instance (required if not using params)
            collection: Optional collection/namespace for keys
            **options: Additional Django cache options (may include WRAPPERS)
        """
        # Handle Django's standard initialization pattern
        if params is None:
            params = {}
        if key_value is None:
            raise ValueError("key_value must be provided")

        # Extract collection from params if not provided
        if collection is None:
            collection = params.get("COLLECTION", "django_cache")

        # Extract wrappers configuration
        wrappers = options.pop("WRAPPERS", None)
        if wrappers is None:
            wrappers = params.get("WRAPPERS", [])

        # Merge params into options
        options.update(params)

        super().__init__(params)

        # Apply wrappers to the key_value store
        self.key_value = self._apply_wrappers(key_value, wrappers)
        self.collection = collection
        self.backend_name = self.__class__.__name__
        self._validate_backend()

    def _apply_wrappers(self, store: KeyValue, wrappers: Optional[list]) -> KeyValue:
        """
        Apply configured wrappers to the key-value store.

        Args:
            store: The base key-value store
            wrappers: List of wrapper configurations, e.g.:
                [{'type': 'encryption', 'key': '...'}, {'type': 'compression'}]

        Returns:
            Wrapped store (or original if no wrappers)
        """
        if not wrappers:
            return store

        for wrapper_config in wrappers:
            if not isinstance(wrapper_config, dict):
                raise ValueError(f"Wrapper config must be a dict, got {type(wrapper_config)}")

            wrapper_type = wrapper_config.get("type")
            if wrapper_type == "encryption":
                from django_kv.encryption import wrap_sync_with_fernet

                key = wrapper_config.get("key")
                store = wrap_sync_with_fernet(store, key=key)
            elif wrapper_type == "compression":
                # Future: add compression wrapper support
                pass
            else:
                raise ValueError(f"Unknown wrapper type: {wrapper_type}")

        return store

    def _validate_backend(self):
        """Validate that the backend implements required methods."""
        required_methods = ["get", "put", "delete"]
        for method in required_methods:
            if not hasattr(self.key_value, method):
                raise AttributeError(f"KeyValue store must implement {method} method")

    def _make_key(self, key: str, version: Optional[int] = None) -> str:
        """
        Construct the cache key with versioning.

        Args:
            key: The base cache key
            version: Optional version number

        Returns:
            Versioned cache key string
        """
        key = force_str(key)
        if version is None:
            version = self.version
        return f"{self.key_prefix}:{version}:{key}"

    def _serialize(self, value: Any) -> Dict[str, Any]:
        """
        Serialize a value for storage.

        Uses pickle for complex objects, JSON for simple types.

        Args:
            value: The value to serialize

        Returns:
            Dictionary with serialized data
        """
        try:
            # Try JSON first for simple types
            json.dumps(value)
            return {"type": "json", "data": value}
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return {"type": "pickle", "data": pickle.dumps(value).hex()}

    def _deserialize(self, stored: Dict[str, Any]) -> Any:
        """
        Deserialize a stored value.

        Args:
            stored: Dictionary with serialized data

        Returns:
            Deserialized value
        """
        if not stored:
            return None

        data_type = stored.get("type")
        data = stored.get("data")

        if data_type == "json":
            return data
        elif data_type == "pickle":
            return pickle.loads(bytes.fromhex(data))
        else:
            # Fallback for raw dicts (backwards compatibility)
            return stored

    def get(self, key: str, version: Optional[int] = None, default: Any = None) -> Any:
        """
        Retrieve a value from the cache.

        Args:
            key: The cache key
            version: Optional version number
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        cache_key = self._make_key(key, version)
        with cache_span(
            "get", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                result = self.key_value.get(key=cache_key, collection=self.collection)
            except Exception:
                record_cache_metrics("get", self.backend_name, error=True)
                return default
        hit = result is not None
        if span:
            span.set_attribute("django_kv.cache.hit", hit)
        record_cache_metrics("get", self.backend_name, hit=hit)
        if result is None:
            return default
        return self._deserialize(result)

    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> None:
        """
        Store a value in the cache.

        Args:
            key: The cache key
            value: The value to store
            timeout: Time-to-live in seconds (None = no expiration)
            version: Optional version number
        """
        cache_key = self._make_key(key, version)
        serialized = self._serialize(value)

        # Convert timeout to float for py-key-value (None = no TTL)
        ttl = float(timeout) if timeout is not None else None
        with cache_span(
            "set", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                self.key_value.put(
                    key=cache_key, value=serialized, collection=self.collection, ttl=ttl
                )
            except Exception:
                record_cache_metrics("set", self.backend_name, error=True)
                return
        if span:
            span.set_attribute("django_kv.cache.ttl", ttl if ttl is not None else -1)
        record_cache_metrics("set", self.backend_name)

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: The cache key
            version: Optional version number

        Returns:
            True if key was deleted, False otherwise
        """
        cache_key = self._make_key(key, version)
        with cache_span(
            "delete", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                result = self.key_value.delete(key=cache_key, collection=self.collection)
            except Exception:
                record_cache_metrics("delete", self.backend_name, error=True)
                return False
        if span:
            span.set_attribute("django_kv.cache.deleted", result)
        record_cache_metrics("delete", self.backend_name, hit=result)
        return result

    def add(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> bool:
        """
        Add a key only if it doesn't already exist.

        Args:
            key: The cache key
            value: The value to store
            timeout: Time-to-live in seconds
            version: Optional version number

        Returns:
            True if key was added, False if it already existed
        """
        # Check if key exists via instrumented get
        existing = self.get(key, version=version, default=None)
        if existing is not None:
            return False

        # Key doesn't exist, set it
        self.set(key, value, timeout, version)
        return True

    def get_many(self, keys: List[str], version: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve multiple values from the cache.

        Args:
            keys: List of cache keys
            version: Optional version number

        Returns:
            Dictionary mapping keys to values (only includes keys that exist)
        """
        if not keys:
            return {}

        cache_keys = [self._make_key(key, version) for key in keys]
        with cache_span(
            "get_many", self.backend_name, self.collection, {"django_kv.cache.key_count": len(keys)}
        ) as span:
            try:
                # py-key-value get_many returns list[dict[str, Any] | None]
                results = self.key_value.get_many(keys=cache_keys, collection=self.collection)
            except Exception:
                record_cache_metrics("get_many", self.backend_name, error=True)
                return {}
        output = {}
        hit_count = 0
        miss_count = 0
        for i, key in enumerate(keys):
            if i < len(results) and results[i] is not None:
                output[key] = self._deserialize(results[i])
                hit_count += 1
            else:
                miss_count += 1
        if span:
            span.set_attribute("django_kv.cache.hit_count", hit_count)
            span.set_attribute("django_kv.cache.miss_count", miss_count)
        record_cache_metrics(
            "get_many", self.backend_name, hit_count=hit_count, miss_count=miss_count
        )
        return output

    def set_many(
        self,
        data: Dict[str, Any],
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> None:
        """
        Store multiple values in the cache.

        Args:
            data: Dictionary mapping keys to values
            timeout: Time-to-live in seconds
            version: Optional version number
        """
        if not data:
            return

        cache_keys = []
        serialized_values = []

        for key, value in data.items():
            cache_keys.append(self._make_key(key, version))
            serialized_values.append(self._serialize(value))

        ttl = float(timeout) if timeout is not None else None
        with cache_span(
            "set_many", self.backend_name, self.collection, {"django_kv.cache.key_count": len(data)}
        ) as span:
            try:
                self.key_value.put_many(
                    keys=cache_keys, values=serialized_values, collection=self.collection, ttl=ttl
                )
            except Exception:
                record_cache_metrics("set_many", self.backend_name, error=True)
                return
        if span:
            span.set_attribute("django_kv.cache.ttl", ttl if ttl is not None else -1)
        record_cache_metrics("set_many", self.backend_name)

    def delete_many(self, keys: List[str], version: Optional[int] = None) -> None:
        """
        Delete multiple keys from the cache.

        Args:
            keys: List of cache keys
            version: Optional version number
        """
        if not keys:
            return

        cache_keys = [self._make_key(key, version) for key in keys]
        with cache_span(
            "delete_many",
            self.backend_name,
            self.collection,
            {"django_kv.cache.key_count": len(keys)},
        ) as span:
            try:
                deleted = self.key_value.delete_many(keys=cache_keys, collection=self.collection)
            except Exception:
                record_cache_metrics("delete_many", self.backend_name, error=True)
                return
        if span:
            span.set_attribute("django_kv.cache.deleted_count", deleted)
        record_cache_metrics("delete_many", self.backend_name, hit_count=deleted)

    def clear(self) -> None:
        """
        Clear all keys in the collection.

        Note: This is a best-effort operation. Some backends may not
        support collection clearing.
        """
        # py-key-value doesn't have a direct clear method
        # This would need to be implemented per-backend if needed
        # For now, we'll raise NotImplementedError
        raise NotImplementedError("clear() is not supported. Use delete_many() with specific keys.")

    def has_key(self, key: str, version: Optional[int] = None) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The cache key
            version: Optional version number

        Returns:
            True if key exists, False otherwise
        """
        cache_key = self._make_key(key, version)
        with cache_span(
            "has_key", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                result = self.key_value.get(key=cache_key, collection=self.collection)
            except Exception:
                record_cache_metrics("has_key", self.backend_name, error=True)
                return False
        hit = result is not None
        if span:
            span.set_attribute("django_kv.cache.hit", hit)
        record_cache_metrics("has_key", self.backend_name, hit=hit)
        return hit
