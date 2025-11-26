"""
Utility functions for Django KV store.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING

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

    else:
        KeyValue = Any  # type: ignore


from django.conf import settings


def get_kv_store_config() -> Dict[str, Any]:
    """
    Retrieve KV store configuration from Django settings.

    Returns:
        Dictionary with KV store configuration

    Example settings:
        KV_STORE = {
            'BACKEND': 'django_kv.backends.memory.MemoryCacheBackend',
            'COLLECTION': 'kv_store',
        }
    """
    return getattr(settings, "KV_STORE", None)


def get_kv_store() -> Optional[KeyValue]:
    """
    Get a standalone KV store instance from Django settings.

    This provides direct access to the py-key-value store without
    going through Django's cache framework.

    Returns:
        KeyValue store instance or None if not configured

    Example:
        from django_kv import get_kv_store

        kv_store = get_kv_store()
        if kv_store:
            kv_store.put(key='user:123', value={'name': 'Alice'}, collection='users')
            user = kv_store.get(key='user:123', collection='users')
    """
    config = get_kv_store_config()
    if not config:
        return None

    backend_class = config.get("BACKEND")
    if not backend_class:
        return None

    # Import the backend class
    module_path, class_name = backend_class.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    backend_class_obj = getattr(module, class_name)

    # Create backend instance - extract options from config
    # Options can be at top level or in OPTIONS dict
    backend_options = config.copy()
    backend_options.pop("BACKEND", None)

    # If OPTIONS exists, merge it with top-level options
    if "OPTIONS" in backend_options:
        options_dict = backend_options.pop("OPTIONS")
        backend_options.update(options_dict)

    backend = backend_class_obj(**backend_options)

    # Return the underlying KeyValue store
    return backend.key_value
