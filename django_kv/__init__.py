"""
Django Key-Value Store Plugin

A pluggable Django cache backend using py-key-value stores.
"""

__version__ = "0.1.0"

from django_kv.utils import get_kv_store

default_app_config = "django_kv.apps.DjangoKvConfig"

__all__ = ["get_kv_store", "default_app_config"]
