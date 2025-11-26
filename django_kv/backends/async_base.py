"""
Base async cache backend class for Django 5.1+ async cache integration.
"""

import pickle
import json
from typing import Any, Optional, Dict, List, TYPE_CHECKING

try:
    from key_value.aio.protocols.key_value import AsyncKeyValue
except ImportError:
    if TYPE_CHECKING:
        from typing import Protocol

        class AsyncKeyValue(Protocol):
            async def get(
                self, key: str, collection: Optional[str] = None
            ) -> Optional[Dict[str, Any]]: ...

            async def put(
                self,
                key: str,
                value: Dict[str, Any],
                collection: Optional[str] = None,
                ttl: Optional[float] = None,
            ) -> None: ...
            async def delete(self, key: str, collection: Optional[str] = None) -> bool: ...

            async def get_many(
                self, keys: List[str], collection: Optional[str] = None
            ) -> List[Optional[Dict[str, Any]]]: ...

            async def put_many(
                self,
                keys: List[str],
                values: List[Dict[str, Any]],
                collection: Optional[str] = None,
                ttl: Optional[float] = None,
            ) -> None: ...

            async def delete_many(
                self, keys: List[str], collection: Optional[str] = None
            ) -> int: ...

    else:
        AsyncKeyValue = Any  # type: ignore

from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.utils.encoding import force_str

from django_kv.observability import cache_span, record_cache_metrics


class AsyncKeyValueCacheBackend(BaseCache):
    """
    Base class for async Django cache backends using py-key-value-aio stores.

    This class bridges Django 5.1+'s async cache framework with py-key-value-aio stores,
    handling serialization, key versioning, and TTL management.
    """

    def __init__(
        self,
        location=None,
        params=None,
        key_value: Optional[AsyncKeyValue] = None,
        collection: Optional[str] = None,
        **options,
    ):
        """
        Initialize the async cache backend.

        Args:
            location: Cache location (unused, for Django compatibility)
            params: Dictionary of cache parameters from settings
            key_value: A py-key-value-aio AsyncKeyValue store instance (required if not using params)
            collection: Optional collection/namespace for keys
            **options: Additional Django cache options (may include WRAPPERS)
        """
        if params is None:
            params = {}
        if key_value is None:
            raise ValueError("key_value must be provided")

        if collection is None:
            collection = params.get("COLLECTION", "django_cache")

        # Extract wrappers configuration
        wrappers = options.pop("WRAPPERS", None)
        if wrappers is None:
            wrappers = params.get("WRAPPERS", [])

        options.update(params)

        super().__init__(params)

        # Apply wrappers to the key_value store
        self.key_value = self._apply_wrappers(key_value, wrappers)
        self.collection = collection
        self.backend_name = self.__class__.__name__
        self._validate_backend()

    def _apply_wrappers(self, store: AsyncKeyValue, wrappers: Optional[list]) -> AsyncKeyValue:
        """
        Apply configured wrappers to the async key-value store.

        Args:
            store: The base async key-value store
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
                from django_kv.encryption import wrap_async_with_fernet

                key = wrapper_config.get("key")
                store = wrap_async_with_fernet(store, key=key)
            elif wrapper_type == "compression":
                # Future: add compression wrapper support
                pass
            else:
                raise ValueError(f"Unknown wrapper type: {wrapper_type}")

        return store

    def _validate_backend(self):
        """Validate that the backend implements required async methods."""
        required_methods = ["get", "put", "delete"]
        for method in required_methods:
            if not hasattr(self.key_value, method):
                raise AttributeError(f"AsyncKeyValue store must implement {method} method")

    def _make_key(self, key: str, version: Optional[int] = None) -> str:
        """Construct the cache key with versioning."""
        key = force_str(key)
        if version is None:
            version = self.version
        return f"{self.key_prefix}:{version}:{key}"

    def _serialize(self, value: Any) -> Dict[str, Any]:
        """Serialize a value for storage."""
        try:
            json.dumps(value)
            return {"type": "json", "data": value}
        except (TypeError, ValueError):
            return {"type": "pickle", "data": pickle.dumps(value).hex()}

    def _deserialize(self, stored: Dict[str, Any]) -> Any:
        """Deserialize a stored value."""
        if not stored:
            return None
        data_type = stored.get("type")
        data = stored.get("data")
        if data_type == "json":
            return data
        elif data_type == "pickle":
            return pickle.loads(bytes.fromhex(data))
        else:
            return stored

    async def aget(self, key: str, version: Optional[int] = None, default: Any = None) -> Any:
        """Async retrieve a value from the cache."""
        cache_key = self._make_key(key, version)
        with cache_span(
            "get", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                result = await self.key_value.get(key=cache_key, collection=self.collection)
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

    async def aset(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> None:
        """Async store a value in the cache."""
        cache_key = self._make_key(key, version)
        serialized = self._serialize(value)
        ttl = float(timeout) if timeout is not None else None
        with cache_span(
            "set", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                await self.key_value.put(
                    key=cache_key, value=serialized, collection=self.collection, ttl=ttl
                )
            except Exception:
                record_cache_metrics("set", self.backend_name, error=True)
                return
        if span:
            span.set_attribute("django_kv.cache.ttl", ttl if ttl is not None else -1)
        record_cache_metrics("set", self.backend_name)

    async def adelete(self, key: str, version: Optional[int] = None) -> bool:
        """Async delete a key from the cache."""
        cache_key = self._make_key(key, version)
        with cache_span(
            "delete", self.backend_name, self.collection, {"django_kv.cache.key": cache_key}
        ) as span:
            try:
                result = await self.key_value.delete(key=cache_key, collection=self.collection)
            except Exception:
                record_cache_metrics("delete", self.backend_name, error=True)
                return False
        if span:
            span.set_attribute("django_kv.cache.deleted", result)
        record_cache_metrics("delete", self.backend_name, hit=result)
        return result

    async def aadd(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> bool:
        """Async add a key only if it doesn't already exist."""
        cache_key = self._make_key(key, version)
        existing = await self.key_value.get(key=cache_key, collection=self.collection)
        if existing is not None:
            return False
        await self.aset(key, value, timeout, version)
        return True

    async def aget_many(self, keys: List[str], version: Optional[int] = None) -> Dict[str, Any]:
        """Async retrieve multiple values from the cache."""
        if not keys:
            return {}
        cache_keys = [self._make_key(key, version) for key in keys]
        with cache_span(
            "get_many", self.backend_name, self.collection, {"django_kv.cache.key_count": len(keys)}
        ) as span:
            try:
                results = await self.key_value.get_many(keys=cache_keys, collection=self.collection)
                output = {}
                for i, key in enumerate(keys):
                    if i < len(results) and results[i] is not None:
                        output[key] = self._deserialize(results[i])
                hit_count = len(output)
                miss_count = len(keys) - hit_count
                if span:
                    span.set_attribute("django_kv.cache.hit_count", hit_count)
                    span.set_attribute("django_kv.cache.miss_count", miss_count)
                record_cache_metrics(
                    "get_many", self.backend_name, hit_count=hit_count, miss_count=miss_count
                )
                return output
            except Exception:
                record_cache_metrics("get_many", self.backend_name, error=True)
                return {}

    async def aset_many(
        self,
        data: Dict[str, Any],
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> None:
        """Async store multiple values in the cache."""
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
                await self.key_value.put_many(
                    keys=cache_keys, values=serialized_values, collection=self.collection, ttl=ttl
                )
            except Exception:
                record_cache_metrics("set_many", self.backend_name, error=True)
                return
        if span:
            span.set_attribute("django_kv.cache.ttl", ttl if ttl is not None else -1)
        record_cache_metrics("set_many", self.backend_name)

    async def adelete_many(self, keys: List[str], version: Optional[int] = None) -> None:
        """Async delete multiple keys from the cache."""
        if not keys:
            return
        cache_keys = [self._make_key(key, version) for key in keys]
        with cache_span(
            "delete_many",
            self.backend_name,
            self.collection,
            {"django_kv.cache.key_count": len(keys)},
        ):
            try:
                await self.key_value.delete_many(keys=cache_keys, collection=self.collection)
            except Exception:
                record_cache_metrics("delete_many", self.backend_name, error=True)
                return
        record_cache_metrics("delete_many", self.backend_name)

    async def ahas_key(self, key: str, version: Optional[int] = None) -> bool:
        """Async check if a key exists in the cache."""
        cache_key = self._make_key(key, version)
        try:
            result = await self.key_value.get(key=cache_key, collection=self.collection)
            return result is not None
        except Exception:
            return False

    # Sync methods delegate to async (for compatibility)
    def get(self, key: str, version: Optional[int] = None, default: Any = None) -> Any:
        """Sync wrapper around aget."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aget(key, version, default))

    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> None:
        """Sync wrapper around aset."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.aset(key, value, timeout, version))

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """Sync wrapper around adelete."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.adelete(key, version))
