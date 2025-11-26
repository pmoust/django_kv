"""
Basic usage examples for django-kv.

This file demonstrates how to use django-kv in a Django project.
"""

# Example 1: Using as Django cache
from django.core.cache import cache

# Set a value
cache.set("user:123", {"name": "Alice", "email": "alice@example.com"}, timeout=3600)

# Get a value
user = cache.get("user:123")
print(f"User: {user}")

# Delete a value
cache.delete("user:123")

# Bulk operations
cache.set_many(
    {
        "key1": "value1",
        "key2": "value2",
        "key3": {"nested": "data"},
    }
)

values = cache.get_many(["key1", "key2", "key3"])
print(f"Bulk values: {values}")

# Example 2: Using standalone KV store
from django_kv import get_kv_store  # noqa: E402

kv_store = get_kv_store()
if kv_store:
    # Direct access to py-key-value store
    kv_store.put(
        key="product:456", value={"name": "Widget", "price": 29.99}, collection="products", ttl=7200
    )

    product = kv_store.get(key="product:456", collection="products")
    print(f"Product: {product}")

# Example 3: Settings configuration
"""
# settings.py

# Development/CI - In-memory
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'django_cache',
    }
}

# Staging - Redis
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.redis.RedisCacheBackend',
        'HOST': 'staging-redis.example.com',
        'PORT': 6379,
        'DB': 0,
        'COLLECTION': 'django_cache',
    }
}

# Standalone KV store
KV_STORE = {
    'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
    'COLLECTION': 'kv_store',
}

# Sessions backed by django-kv
SESSION_ENGINE = 'django_kv.sessions'
DJANGO_KV_SESSION_CACHE_ALIAS = 'django_kv_sessions'
CACHES['django_kv_sessions'] = {
    'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
    'COLLECTION': 'session_cache',
}

# Async cache backend (Django 5.1+)
CACHES = {
    'async_default': {
        'BACKEND': 'django_kv.backends.async_memory.AsyncMemoryCacheBackend',
        'COLLECTION': 'django_cache',
    }
}

# Async sessions
SESSION_ENGINE = 'django_kv.sessions_async'
CACHES['django_kv_sessions_async'] = {
    'BACKEND': 'django_kv.backends.async_memory.AsyncMemoryCacheBackend',
    'COLLECTION': 'session_cache',
}

# Encrypted sessions
SESSION_ENGINE = 'django_kv.sessions_encrypted'
# Encryption key defaults to SECRET_KEY, or set explicitly:
# DJANGO_KV_ENCRYPTION_KEY = 'base64-encoded-fernet-key'

# Cache with wrappers (encryption, compression, etc.)
CACHES = {
    'secure_cache': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'secure_data',
        'WRAPPERS': [
            {'type': 'encryption'},  # Automatically uses SECRET_KEY
        ],
    },
}

# Optional: OpenTelemetry integration
from django_kv.otel import init_tracing

DJANGO_KV_OTEL = {
    "ENABLED": True,
    "INSTRUMENT_CACHE": True,
    "INSTRUMENT_SESSIONS": True,
    "METRICS_ENABLED": True,
}

init_tracing(service_name="example-app", endpoint="http://localhost:4317")
"""
