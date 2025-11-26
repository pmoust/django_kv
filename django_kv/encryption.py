"""
Encryption wrappers for py-key-value stores.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any, Optional

from django.conf import settings  # type: ignore
from django.core.exceptions import ImproperlyConfigured  # type: ignore

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover
    Fernet = None  # type: ignore

try:
    from key_value.aio.protocols.key_value import AsyncKeyValue
    from key_value.aio.wrappers.encryption import FernetEncryptionWrapper as AsyncFernetWrapper
except ImportError:  # pragma: no cover
    AsyncKeyValue = Any  # type: ignore
    AsyncFernetWrapper = None  # type: ignore

try:
    from key_value.sync.protocols.key_value import KeyValue
    from key_value.sync.wrappers.encryption import FernetEncryptionWrapper as SyncFernetWrapper
except ImportError:  # pragma: no cover
    KeyValue = Any  # type: ignore
    SyncFernetWrapper = None  # type: ignore


def _derive_fernet_key_from_secret_key(secret_key: str) -> bytes:
    """
    Derive a Fernet-compatible key (32 bytes, URL-safe base64) from Django's SECRET_KEY.

    Fernet requires a 32-byte key. We use SHA256 to hash the SECRET_KEY and use the result.
    """
    if Fernet is None:
        raise ImproperlyConfigured("cryptography must be installed to use encryption")

    # Hash the secret key to get exactly 32 bytes
    hashed = hashlib.sha256(secret_key.encode("utf-8")).digest()
    # Base64-encode the hashed key to make it URL-safe (Fernet expects URL-safe base64)
    return base64.urlsafe_b64encode(hashed)


def _get_fernet_key(key: Optional[str | bytes] = None) -> bytes:
    """
    Resolve a Fernet key from settings or provided value.

    Priority:
    1. Explicitly provided key
    2. DJANGO_KV_ENCRYPTION_KEY setting
    3. Derived from Django's SECRET_KEY
    """
    if Fernet is None:
        raise ImproperlyConfigured("cryptography must be installed to use encryption")

    # Explicit key provided
    if key:
        if isinstance(key, str):
            # If it's a string, try to decode it as base64, otherwise derive from it
            try:
                return base64.urlsafe_b64decode(key.encode("utf-8"))
            except Exception:
                # If it's not valid base64, derive from it
                return _derive_fernet_key_from_secret_key(key)
        return key

    # Check settings for explicit encryption key
    encryption_key = getattr(settings, "DJANGO_KV_ENCRYPTION_KEY", None)
    if encryption_key:
        if isinstance(encryption_key, bytes):
            return encryption_key
        if isinstance(encryption_key, str):
            try:
                import base64

                return base64.urlsafe_b64decode(encryption_key.encode("utf-8"))
            except Exception:
                return _derive_fernet_key_from_secret_key(encryption_key)

    # Fall back to deriving from SECRET_KEY
    django_secret_key = getattr(settings, "SECRET_KEY", None)
    if django_secret_key:
        logger.info("Deriving encryption key from Django SECRET_KEY")
        return _derive_fernet_key_from_secret_key(django_secret_key)

    raise ImproperlyConfigured(
        "DJANGO_KV_ENCRYPTION_KEY or SECRET_KEY must be set to use encryption. "
        "For production, explicitly set DJANGO_KV_ENCRYPTION_KEY."
    )


def wrap_async_with_fernet(
    key_value: AsyncKeyValue, key: Optional[str | bytes] = None
) -> AsyncKeyValue:
    """
    Wrap an AsyncKeyValue in a Fernet encryption wrapper.

    Args:
        key_value: The async key-value store to wrap
        key: Optional Fernet key (bytes or base64-encoded string).
             If None, derives from DJANGO_KV_ENCRYPTION_KEY or SECRET_KEY.

    Returns:
        Encrypted AsyncKeyValue wrapper
    """
    if AsyncFernetWrapper is None:
        raise ImportError("Async encryption requires py-key-value-aio[encryption]")
    fernet_key = _get_fernet_key(key)
    return AsyncFernetWrapper(key_value=key_value, key=fernet_key)


def wrap_sync_with_fernet(key_value: KeyValue, key: Optional[str | bytes] = None) -> KeyValue:
    """
    Wrap a sync KeyValue in a Fernet encryption wrapper.

    Args:
        key_value: The sync key-value store to wrap
        key: Optional Fernet key (bytes or base64-encoded string).
             If None, derives from DJANGO_KV_ENCRYPTION_KEY or SECRET_KEY.

    Returns:
        Encrypted KeyValue wrapper
    """
    if SyncFernetWrapper is None:
        raise ImportError("Sync encryption requires py-key-value-sync[encryption]")
    fernet_key = _get_fernet_key(key)
    return SyncFernetWrapper(key_value=key_value, key=fernet_key)
