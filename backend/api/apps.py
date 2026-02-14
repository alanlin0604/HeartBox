import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        import os
        if not os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes'):
            if not os.getenv('REDIS_URL'):
                logger.warning(
                    'REDIS_URL is not set in production. '
                    'WebSocket channel layer and cache will use in-memory backends '
                    'which do not work across multiple processes.'
                )
