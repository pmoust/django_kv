"""
Redis cache backend using py-key-value RedisStore.

Ideal for staging and production environments requiring distributed caching.
"""

from typing import Optional
from django_kv.backends.base import KeyValueCacheBackend

try:
    from key_value.sync.stores.redis import RedisStore
except ImportError:
    RedisStore = None


class RedisCacheBackend(KeyValueCacheBackend):
    """
    Django cache backend using Redis storage.

    This backend uses py-key-value's RedisStore, providing distributed
    caching suitable for staging and production environments.

    Configuration example:
        CACHES = {
            'default': {
                'BACKEND': 'django_kv.backends.redis.RedisCacheBackend',
                'HOST': 'localhost',
                'PORT': 6379,
                'DB': 0,
                'COLLECTION': 'django_cache',
            }
        }
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        collection: str = "django_cache",
        **options,
    ):
        """
        Initialize the Redis cache backend.

        Args:
            host: Redis host (default: 'localhost')
            port: Redis port (default: 6379)
            db: Redis database number (default: 0)
            password: Optional Redis password
            collection: Collection/namespace for keys (default: 'django_cache')
            **options: Additional Django cache options (KEY_PREFIX, VERSION, etc.)
        """
        if RedisStore is None:
            raise ImportError(
                "RedisStore is not available. Install py-key-value with Redis support: "
                "pip install py-key-value[redis]"
            )

        # Build connection parameters
        redis_kwargs = {
            "host": host,
            "port": port,
            "db": db,
        }
        if password:
            redis_kwargs["password"] = password

        store = RedisStore(**redis_kwargs)
        super().__init__(key_value=store, collection=collection, **options)
