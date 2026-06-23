import logging
import os
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _is_management_command_skipping_warmup() -> bool:
    """``apps.ready()`` runs for every management command. We must NOT
    eager-load bge-m3 during ``migrate`` / ``collectstatic`` / ``test``
    etc. — those commands do not need the embedder and the import cost
    bloats CI runtime + breaks ``--keepdb`` flows that don't have a
    knowledge base.
    """
    import sys
    skip_commands = {
        'migrate', 'makemigrations', 'collectstatic', 'createsuperuser',
        'shell', 'shell_plus', 'dbshell', 'test', 'testserver',
        'check', 'showmigrations', 'sqlmigrate', 'loaddata', 'dumpdata',
        'load_knowledge_base',  # this command builds the embedder itself
    }
    if len(sys.argv) >= 2 and sys.argv[1] in skip_commands:
        return True
    return False


def _prewarm_bge_m3_async() -> None:
    """Spawn a daemon thread that touches the bge-m3 retriever once so the
    expensive ``sentence-transformers`` model load (5-30 s cold) is paid
    in the background during process startup, NOT on the first user
    request. Failures are logged and swallowed — pre-warm is best-effort,
    not a hard dependency.

    Adversarial review flagged the cold-start latency as a demo-day
    risk (``apps.ready()`` cold start + first-request latency would
    eat the 5-second budget on the daily-prompt feedback box).
    """
    if _is_management_command_skipping_warmup():
        return

    def _warm():
        try:
            from api.services.ai_engine import ai_engine
            # _get_retriever() is the entry point that lazy-loads bge-m3
            # via langchain_chroma.Chroma + BgeM3Embeddings. If ChromaDB
            # is empty / not configured it returns None gracefully — but
            # the embedder is still instantiated, which is the warm-up
            # we care about.
            retriever = ai_engine._get_retriever()
            logger.info(
                'bge-m3 pre-warm complete (retriever=%s)',
                'ready' if retriever is not None else 'empty-collection',
            )
        except Exception:  # pragma: no cover — best-effort
            logger.exception('bge-m3 pre-warm failed; first request will pay full cold-start cost')

    threading.Thread(target=_warm, name='bge-m3-prewarm', daemon=True).start()


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        if not os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes'):
            if not os.getenv('REDIS_URL'):
                logger.warning(
                    'REDIS_URL is not set in production. '
                    'WebSocket channel layer and cache will use in-memory backends '
                    'which do not work across multiple processes.'
                )

        # Eager-load bge-m3 on background thread so the first user-facing
        # RAG call doesn't pay the 5-30 s cold-start tax. Opt-out via
        # ``DISABLE_AI_PREWARM=1`` (useful for some test environments).
        if not os.getenv('DISABLE_AI_PREWARM'):
            _prewarm_bge_m3_async()
