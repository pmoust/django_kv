"""
Settings validation for django-kv.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings  # type: ignore
from django.core.exceptions import ImproperlyConfigured  # type: ignore

logger = logging.getLogger(__name__)


def validate_cache_config(cache_alias: str, cache_config: Dict[str, Any]) -> None:
    """
    Validate a single cache configuration.

    Args:
        cache_alias: The cache alias name
        cache_config: The cache configuration dictionary

    Raises:
        ImproperlyConfigured: If configuration is invalid
    """
    backend = cache_config.get("BACKEND", "")

    # Check if it's a django-kv backend
    if not backend.startswith("django_kv."):
        return  # Not our concern

    # Validate required fields
    if "COLLECTION" not in cache_config and "COLLECTION" not in cache_config.get("OPTIONS", {}):
        logger.warning(
            f"Cache '{cache_alias}' uses django-kv backend but no COLLECTION specified. "
            "Defaulting to 'django_cache'."
        )

    # Validate wrappers if present
    wrappers = cache_config.get("WRAPPERS", [])
    if wrappers:
        if not isinstance(wrappers, list):
            raise ImproperlyConfigured(
                f"Cache '{cache_alias}': WRAPPERS must be a list, got {type(wrappers)}"
            )
        for i, wrapper in enumerate(wrappers):
            if not isinstance(wrapper, dict):
                raise ImproperlyConfigured(
                    f"Cache '{cache_alias}': WRAPPERS[{i}] must be a dict, got {type(wrapper)}"
                )
            wrapper_type = wrapper.get("type")
            if wrapper_type == "encryption":
                # Encryption wrapper is valid
                pass
            elif wrapper_type == "compression":
                # Compression wrapper (future)
                pass
            else:
                raise ImproperlyConfigured(
                    f"Cache '{cache_alias}': WRAPPERS[{i}] has unknown type '{wrapper_type}'. "
                    "Supported: 'encryption', 'compression'"
                )


def validate_session_config() -> None:
    """
    Validate session configuration if using django-kv session backends.

    Raises:
        ImproperlyConfigured: If configuration is invalid
    """
    session_engine = getattr(settings, "SESSION_ENGINE", None)
    if not session_engine or not session_engine.startswith("django_kv."):
        return  # Not using django-kv sessions

    # Check that the session cache alias exists
    session_cache_alias = getattr(
        settings,
        "DJANGO_KV_SESSION_CACHE_ALIAS",
        getattr(settings, "SESSION_CACHE_ALIAS", "django_kv_sessions"),
    )

    caches = getattr(settings, "CACHES", {})
    if session_cache_alias not in caches:
        raise ImproperlyConfigured(
            f"Session engine '{session_engine}' requires cache alias '{session_cache_alias}' "
            "to exist in CACHES setting."
        )

    # Validate the cache backend is a django-kv backend
    cache_config = caches[session_cache_alias]
    cache_backend = cache_config.get("BACKEND", "")
    if not cache_backend.startswith("django_kv."):
        logger.warning(
            f"Session engine '{session_engine}' uses cache alias '{session_cache_alias}' "
            f"with non-django-kv backend '{cache_backend}'. This may not work as expected."
        )


def validate_all_settings() -> None:
    """
    Validate all django-kv related settings.

    This should be called during Django app initialization (e.g., in AppConfig.ready()).

    Raises:
        ImproperlyConfigured: If any configuration is invalid
    """
    # Validate all cache configurations
    caches = getattr(settings, "CACHES", {})
    for alias, config in caches.items():
        try:
            validate_cache_config(alias, config)
        except ImproperlyConfigured:
            raise
        except Exception as e:
            logger.warning(f"Error validating cache '{alias}': {e}")

    # Validate session configuration
    try:
        validate_session_config()
    except ImproperlyConfigured:
        raise
    except Exception as e:
        logger.warning(f"Error validating session config: {e}")
