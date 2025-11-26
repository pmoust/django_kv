"""
Pytest configuration for django-kv tests.
"""

from pathlib import Path
import sys

import django
from django.conf import settings

# Ensure py-key-value is available (either installed or vendored locally).
try:
    import key_value  # noqa: F401
except ImportError:  # pragma: no cover - setup logic
    repo_root = Path(__file__).resolve().parents[1]
    candidate_paths = [
        repo_root / "external" / "py-key-value" / "key-value" / "key-value-sync" / "src",
        repo_root / "external" / "py-key-value" / "key-value" / "key-value-shared" / "src",
    ]
    for path in candidate_paths:
        if path.exists():
            sys.path.insert(0, str(path))

    import key_value  # type: ignore  # noqa: F401

# Configure Django settings for tests
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-secret-key-for-testing-only",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
        ],
        CACHES={
            "default": {
                "BACKEND": "django_kv.backends.memory.MemoryCacheBackend",
                "COLLECTION": "test_cache",
            }
        },
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    )
    django.setup()
