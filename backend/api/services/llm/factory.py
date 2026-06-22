"""Factory for the singleton LLMProvider.

Dispatches on ``settings.LLM_PROVIDER``. Exactly two backends are supported
in production code as of the Phase 0b OpenAI cut-over:

* ``remote_taide`` (default) – ``RemoteTAIDEProvider`` talking to the FastAPI
  inference server (TAIDE/LLaVA) over an OpenAI-compatible HTTP API.
* ``mock`` – ``MockProvider`` for unit tests. Deterministic, no network.

Any other value raises ``LLMProviderError`` at construction. There is NO
``openai`` provider — that branch was removed deliberately so the OpenAI
escape hatch can't be flipped back on by a misconfigured env var without
re-adding the dependency.

Singleton with double-checked locking to mirror the existing ``AIEngine``
pattern — required because ``_run_full_analysis`` is sometimes called from
a ``threading.Thread`` worker in ``views/notes.py``.
"""
from __future__ import annotations

import logging
import threading

from django.conf import settings

from .base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

_provider: LLMProvider | None = None
_lock = threading.Lock()


def get_llm_provider() -> LLMProvider:
    """Return the singleton provider, constructing it on first call."""
    global _provider
    if _provider is not None:
        return _provider

    with _lock:
        if _provider is not None:
            return _provider

        backend = getattr(settings, 'LLM_PROVIDER', 'remote_taide')

        if backend == 'mock':
            from .mock_provider import MockProvider
            _provider = MockProvider()
        elif backend == 'remote_taide':
            from .remote_provider import RemoteTAIDEProvider
            _provider = RemoteTAIDEProvider(
                base_url=getattr(settings, 'LLM_SERVER_URL', ''),
                api_key=getattr(settings, 'LLM_SERVER_API_KEY', ''),
                chat_model=getattr(settings, 'LLM_MODEL', 'taide-lx-7b-chat'),
                vision_model=getattr(settings, 'LLM_VISION_MODEL', 'llava-v1.6-mistral-7b'),
                timeout_s=getattr(settings, 'LLM_TIMEOUT_S', 30.0),
            )
        else:
            raise LLMProviderError(
                f'Unknown LLM_PROVIDER={backend!r}. '
                "Expected 'remote_taide' or 'mock'."
            )

        logger.info('LLM provider initialised: %s', _provider.name)
        return _provider


def reset_llm_provider_cache() -> None:
    """Clear the singleton. Used in tests after ``override_settings``."""
    global _provider
    with _lock:
        _provider = None
