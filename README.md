# Django Key-Value Store Plugin

[![CI](https://github.com/pmoust/django_kv/actions/workflows/ci.yml/badge.svg)](https://github.com/pmoust/django_kv/actions/workflows/ci.yml)

A pluggable Django cache backend using [py-key-value](https://github.com/strawgate/py-key-value) stores. This plugin allows you to easily switch between different key-value store backends (in-memory for dev/CI, Redis for staging/production) while maintaining a consistent interface across environments.

## Features

- ✅ **Multiple Backend Support**: Memory (dev/CI), Redis (staging/production), Disk (single-host persistence)
- ✅ **Local Persistence**: Disk-based cache for single-host deployments
- ✅ **Django Cache Framework Compatible**: Drop-in replacement for Django's cache
- ✅ **Easy Configuration**: Simple settings-based backend switching
- ✅ **Full Feature Support**: TTL, bulk operations, key versioning
- ✅ **Type Safety**: Handles complex objects with automatic serialization
- ✅ **Observability Ready**: Optional OpenTelemetry traces and metrics for cache & session ops

## Installation

### Requirements

- Python **3.10+** (the upstream `py-key-value` project requires match statements)
- `beartype` and `cachetools` (installed via `requirements-dev.txt`)
- `py-key-value-sync>=0.3.0` (installed automatically as a dependency)

```bash
pip install django-kv
```

For Redis support:
```bash
pip install "django-kv[redis]"
```

For OpenTelemetry helpers:
```bash
pip install "django-kv[otel]"
```

## Quick Start

### Async-first usage (recommended)

```python
from django_kv.aio import get_async_kv_store

async def example():
    store = await get_async_kv_store()
    # Default is an in-memory AsyncKeyValue
    await store.put(key="user:1", value={"name": "Alice"}, collection="users", ttl=3600)
    user = await store.get(key="user:1", collection="users")
    return user
```

Configure the async store (optional):

```python
# settings.py
ASYNC_KV_STORE = {
    "BACKEND": "memory",  # redis, disk, etc.
    "OPTIONS": {},        # forwarded to py-key-value-aio MemoryStore
}
```

### Django cache (sync)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'django_cache',
    }
}
```

Usage:

```python
from django.core.cache import cache

cache.set('my_key', {'data': 'value'}, timeout=3600)
value = cache.get('my_key')
cache.delete('my_key')
```

## Configuration

### Memory Backend

Perfect for development and CI environments:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'django_cache',  # Optional, defaults to 'django_cache'
    }
}
```

### Redis Backend

Ideal for staging and production:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.redis.RedisCacheBackend',
        'HOST': 'localhost',           # Redis host
        'PORT': 6379,                  # Redis port
        'DB': 0,                       # Redis database number
        'PASSWORD': None,              # Optional Redis password
        'COLLECTION': 'django_cache',  # Optional collection/namespace
    }
}
```

## Standalone KV Store

You can also use the sync KV store directly without going through Django's cache framework:

```python
# settings.py
KV_STORE = {
    'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
    'COLLECTION': 'kv_store',
}

# In your code
from django_kv import get_kv_store

kv_store = get_kv_store()
if kv_store:
    kv_store.put(key='user:123', value={'name': 'Alice'}, collection='users')
    user = kv_store.get(key='user:123', collection='users')
```

### Encryption wrapper (async and sync)

```python
from django_kv.aio import get_async_kv_store
from django_kv.encryption import wrap_async_with_fernet

async def encrypted_example():
    base_store = await get_async_kv_store()
    # Key is optional - defaults to DJANGO_KV_ENCRYPTION_KEY or SECRET_KEY
    secure_store = wrap_async_with_fernet(base_store)
    await secure_store.put(key="secret", value={"token": "..."},
                           collection="secrets", ttl=600)
```

### Wrapper Configuration

Configure wrappers (encryption, compression, etc.) directly in cache settings:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'django_cache',
        'WRAPPERS': [
            {'type': 'encryption'},  # Uses SECRET_KEY or DJANGO_KV_ENCRYPTION_KEY
            # Future: {'type': 'compression'},
        ],
    },
}
```

## Sessions

Use django-kv as a Django session backend by pointing the session engine at
`django_kv.sessions` and configuring a dedicated cache alias.

### Sync Sessions (Development / CI - Memory)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'django_cache',
    },
    'django_kv_sessions': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'session_cache',
    },
}

SESSION_ENGINE = 'django_kv.sessions'
# Optional: customize alias name
# DJANGO_KV_SESSION_CACHE_ALIAS = 'django_kv_sessions'
```

### Async Sessions (Django 5.1+)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.async_memory.AsyncMemoryCacheBackend',
        'COLLECTION': 'django_cache',
    },
    'django_kv_sessions_async': {
        'BACKEND': 'django_kv.backends.async_memory.AsyncMemoryCacheBackend',
        'COLLECTION': 'session_cache',
    },
}

SESSION_ENGINE = 'django_kv.sessions_async'
# Optional: customize alias name
# DJANGO_KV_SESSION_CACHE_ALIAS = 'django_kv_sessions_async'
```

### Encrypted Sessions

For sensitive session data, use the encrypted session backend:

```python
# settings.py
CACHES = {
    'django_kv_sessions': {
        'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
        'COLLECTION': 'session_cache',
    },
}

SESSION_ENGINE = 'django_kv.sessions_encrypted'
# Optional: explicit encryption key (defaults to SECRET_KEY)
# DJANGO_KV_ENCRYPTION_KEY = 'base64-encoded-fernet-key'
```

### Production (Redis)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.redis.RedisCacheBackend',
        'HOST': 'redis-prod.internal',
        'PORT': 6379,
        'COLLECTION': 'django_cache',
    },
    'redis_sessions': {
        'BACKEND': 'django_kv.backends.redis.RedisCacheBackend',
        'HOST': 'redis-prod.internal',
        'PORT': 6379,
        'DB': 1,
        'COLLECTION': 'session_cache',
    },
}

SESSION_ENGINE = 'django_kv.sessions'
DJANGO_KV_SESSION_CACHE_ALIAS = 'redis_sessions'
```

### Single-host persistence (Disk)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_kv.backends.disk.DiskCacheBackend',
        'DIRECTORY': '/var/cache/django-kv/default',
        'MAX_SIZE': 10 * 1024 * 1024 * 1024,  # 10GB
        'COLLECTION': 'django_cache',
    }
}
```

## Observability (OpenTelemetry)

Enable spans/metrics for cache and session operations:

```python
INSTALLED_APPS = [
    # ...
    'django_kv',
]

DJANGO_KV_OTEL = {
    "ENABLED": True,
    "INSTRUMENT_CACHE": True,
    "INSTRUMENT_SESSIONS": True,
    "METRICS_ENABLED": True,
    "AUTO_INSTRUMENT_DJANGO": True,  # automatically instruments Django
}
```

Initialize tracing (e.g. OTLP) before Django starts:

```python
# wsgi.py / manage.py
from django_kv.otel import init_tracing

init_tracing(service_name="my-django-app", endpoint="http://otel-collector:4317")
```

Or use the standard `opentelemetry-instrument python manage.py runserver` workflow. The
cache/session spans are emitted when `DJANGO_KV_OTEL["ENABLED"]` is set.

## Development

### Setup (Python 3.12 example, from source)

```bash
# Clone the repository
git clone https://github.com/pmoust/django_kv.git
cd django_kv

# (Recommended) Create a Python 3.12 virtual environment
/opt/homebrew/bin/python3.12 -m venv .venv3.12
source .venv3.12/bin/activate

# Install development dependencies (Django, pytest, etc.)
pip install -r requirements-dev.txt
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black django_kv tests

# Lint code
flake8 django_kv tests

# Type checking
mypy django_kv
```

## Project Status

This project is **production-ready** (v0.1.0). Current status:

- ✅ Memory backend (sync & async) - fully functional
- ✅ Redis backend - fully functional
- ✅ Disk backend - fully functional
- ✅ Async cache and session backends (Django 5.1+)
- ✅ Encrypted session backend
- ✅ OpenTelemetry instrumentation
- ✅ Wrapper configuration system (encryption)
- ✅ Settings validation
- ✅ Comprehensive test suite
- ✅ CI/CD pipeline

### Test Matrix

The project is tested across multiple combinations:

- **Python Versions**: 3.10, 3.11, 3.12, 3.13, 3.14
- **Django Versions**: 5.1, 5.2
- **py-key-value Versions**: 0.3.0 (stable release), main (latest)

This results in **20 test combinations** (5 Python × 2 Django × 2 py-key-value versions) plus **5 lint jobs** (one per Python version).

See the [CI workflow](https://github.com/pmoust/django_kv/actions/workflows/ci.yml) for the latest test results.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on top of [py-key-value](https://github.com/strawgate/py-key-value) by @strawgate
- Inspired by Django's flexible cache framework

## Links

- [py-key-value Documentation](https://github.com/strawgate/py-key-value)
- [Django Cache Framework](https://docs.djangoproject.com/en/stable/topics/cache/)

