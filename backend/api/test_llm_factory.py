"""Unit tests for ``api.services.llm.factory``.

The factory is the single dispatch point that decides which LLM
provider serves the live request. Three invariants must hold and are
pinned here:

1. ``LLM_PROVIDER='openai'`` (the legacy escape hatch) MUST raise. The
   factory docstring explicitly states the OpenAI branch was removed
   "so the OpenAI escape hatch can't be flipped back on by a
   misconfigured env var without re-adding the dependency."

2. Singleton cache must actually cache (calling twice returns the
   SAME instance) AND must reset cleanly via
   ``reset_llm_provider_cache()`` so test ``override_settings`` works.

3. Concurrent calls during cache miss must not produce two providers
   (double-checked locking pattern).

Run with:
    python manage.py test api.test_llm_factory
"""
import threading
import unittest

from django.test import override_settings

from api.services.llm.base import LLMProviderError
from api.services.llm.factory import get_llm_provider, reset_llm_provider_cache


class FactoryTestCaseBase(unittest.TestCase):
    """Reset the singleton both before AND after each test so cache
    state never leaks between tests."""

    def setUp(self):
        reset_llm_provider_cache()

    def tearDown(self):
        reset_llm_provider_cache()


class TestFactoryDispatch(FactoryTestCaseBase):

    @override_settings(LLM_PROVIDER='mock', LLM_MOCK_CONFIGURED=False)
    def test_mock_provider_returned_when_configured(self):
        provider = get_llm_provider()
        self.assertEqual(provider.name, 'mock')

    @override_settings(LLM_PROVIDER='remote_taide', LLM_SERVER_URL='', LLM_SERVER_API_KEY='')
    def test_remote_taide_default_returned(self):
        provider = get_llm_provider()
        self.assertEqual(provider.name, 'remote_taide')

    @override_settings(LLM_PROVIDER='openai')
    def test_openai_value_raises(self):
        """The OpenAI escape hatch was deliberately removed. If anyone
        flips ``LLM_PROVIDER=openai`` in env, the factory must REFUSE
        to construct a provider — otherwise journal content could
        silently route to OpenAI again."""
        with self.assertRaises(LLMProviderError) as ctx:
            get_llm_provider()
        self.assertIn("'openai'", str(ctx.exception).lower().replace('"', "'"))

    @override_settings(LLM_PROVIDER='gpt-4')
    def test_any_unknown_value_raises(self):
        with self.assertRaises(LLMProviderError):
            get_llm_provider()

    @override_settings(LLM_PROVIDER='REMOTE_TAIDE')
    def test_uppercase_not_accepted(self):
        """LLM_PROVIDER comparison is case-sensitive — uppercase
        ``REMOTE_TAIDE`` is NOT silently coerced to lowercase. Future
        operators who follow a stale doc and set the wrong case get
        a hard error instead of silent fallback."""
        with self.assertRaises(LLMProviderError):
            get_llm_provider()


class TestFactorySingleton(FactoryTestCaseBase):

    @override_settings(LLM_PROVIDER='mock', LLM_MOCK_CONFIGURED=False)
    def test_singleton_returns_same_instance(self):
        p1 = get_llm_provider()
        p2 = get_llm_provider()
        self.assertIs(p1, p2)

    @override_settings(LLM_PROVIDER='mock', LLM_MOCK_CONFIGURED=False)
    def test_cache_is_sticky_without_reset(self):
        """Once a provider is cached, changing settings without calling
        ``reset_llm_provider_cache()`` does NOT change the returned
        provider. This is the contract every test using
        ``@override_settings`` relies on understanding."""
        first = get_llm_provider()
        # Override LLM_PROVIDER to an invalid value INSIDE the test.
        # Without reset_llm_provider_cache(), the cached mock wins.
        with override_settings(LLM_PROVIDER='gpt-4-turbo'):
            second = get_llm_provider()
        self.assertIs(first, second)
        self.assertEqual(second.name, 'mock')

    @override_settings(LLM_PROVIDER='mock', LLM_MOCK_CONFIGURED=False)
    def test_reset_actually_resets(self):
        first = get_llm_provider()
        reset_llm_provider_cache()
        with override_settings(LLM_PROVIDER='gpt-4-turbo'):
            with self.assertRaises(LLMProviderError):
                get_llm_provider()
        # And the original cache slot is now empty / re-fetchable.
        second = get_llm_provider()
        self.assertEqual(second.name, 'mock')
        # New instance, not the old one.
        self.assertIsNot(first, second)


class TestFactoryConcurrent(FactoryTestCaseBase):

    @override_settings(LLM_PROVIDER='mock', LLM_MOCK_CONFIGURED=False)
    def test_concurrent_first_calls_return_same_instance(self):
        """Two threads racing into ``get_llm_provider()`` on a cold
        cache must NOT produce two different provider objects.
        Double-checked locking inside factory.py prevents this."""
        results = []
        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()
            results.append(get_llm_provider())

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(len(results), 8)
        first = results[0]
        for r in results[1:]:
            self.assertIs(
                r, first,
                'Concurrent get_llm_provider() returned different '
                'instances — double-checked locking is broken',
            )


if __name__ == '__main__':
    unittest.main()
