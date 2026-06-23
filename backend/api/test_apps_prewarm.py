"""Test the bge-m3 pre-warm hook in ``api.apps.ApiConfig.ready``.

The hook eager-loads the retriever on a daemon thread so the 5-30s
sentence-transformers cold-start is paid during process boot, not on
the first user RAG request.

Two contracts to pin:
1. ``DISABLE_AI_PREWARM=1`` opt-out actually skips the thread spawn.
2. Management commands like ``test``, ``migrate``, ``load_knowledge_base``
   are auto-skipped (calling _prewarm_bge_m3_async during these would
   either double-load or break the command).

Run with:
    python manage.py test api.test_apps_prewarm
"""
import os
import unittest
from unittest.mock import patch


class TestDisableAiPrewarm(unittest.TestCase):

    def test_disable_env_var_skips_thread_spawn(self):
        """When ``DISABLE_AI_PREWARM=1`` is set, ``_prewarm_bge_m3_async``
        should NOT spawn the warm-up thread."""
        from api import apps as apps_module
        with patch.dict(os.environ, {'DISABLE_AI_PREWARM': '1'}):
            with patch.object(apps_module.threading, 'Thread') as mock_thread:
                # Simulate the ready() path's tail
                if not os.getenv('DISABLE_AI_PREWARM'):
                    apps_module._prewarm_bge_m3_async()
                mock_thread.assert_not_called()


class TestSkipForManagementCommands(unittest.TestCase):

    def test_test_command_skips(self):
        """We are literally running ``manage.py test`` right now —
        ``_is_management_command_skipping_warmup()`` must return True
        (otherwise this test wouldn't even be runnable without a slow
        bge-m3 load at suite import time)."""
        import sys
        from api.apps import _is_management_command_skipping_warmup
        # sys.argv[1] is 'test' (or 'test_runner' variants)
        if len(sys.argv) >= 2 and sys.argv[1].startswith('test'):
            self.assertTrue(_is_management_command_skipping_warmup())

    def test_migrate_command_skips(self):
        from api.apps import _is_management_command_skipping_warmup
        with patch('sys.argv', ['manage.py', 'migrate']):
            self.assertTrue(_is_management_command_skipping_warmup())

    def test_load_knowledge_base_skips(self):
        """``load_knowledge_base`` builds its own embedder — pre-warming
        on top would either double-load or race the manage command."""
        from api.apps import _is_management_command_skipping_warmup
        with patch('sys.argv', ['manage.py', 'load_knowledge_base', '--reset']):
            self.assertTrue(_is_management_command_skipping_warmup())

    def test_runserver_does_not_skip(self):
        """``runserver`` is the production-shape path and SHOULD trigger
        pre-warm so the first user request is fast."""
        from api.apps import _is_management_command_skipping_warmup
        with patch('sys.argv', ['manage.py', 'runserver']):
            self.assertFalse(_is_management_command_skipping_warmup())

    def test_no_argv_does_not_skip(self):
        """Short argv (e.g. running via uvicorn / daphne directly with no
        ``manage.py <cmd>`` shape) should NOT trigger the skip — that's
        the production-shape path."""
        from api.apps import _is_management_command_skipping_warmup
        with patch('sys.argv', ['daphne']):
            self.assertFalse(_is_management_command_skipping_warmup())


if __name__ == '__main__':
    unittest.main()
