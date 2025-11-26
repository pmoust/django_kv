"""
App configuration for django-kv.
"""

from __future__ import annotations

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DjangoKvConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "django_kv"

    def ready(self):
        # Automatically wire OTEL instrumentation if enabled.
        from django_kv import observability

        observability.auto_instrument_django()

        # Validate settings
        try:
            from django_kv.validation import validate_all_settings

            validate_all_settings()
        except Exception as e:
            logger.warning(f"Settings validation warning: {e}")
