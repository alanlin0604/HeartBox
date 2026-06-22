"""LLM provider seam.

Single import surface for the rest of the Django app. Callers should only
ever touch:

    from api.services.llm import get_llm_provider, LLMProviderError

Switching backend (TAIDE / OpenAI / mock) happens via the
``LLM_PROVIDER`` Django setting, not via direct imports of provider classes.
"""
from .base import LLMProvider, LLMProviderError
from .factory import get_llm_provider, reset_llm_provider_cache

__all__ = [
    'LLMProvider',
    'LLMProviderError',
    'get_llm_provider',
    'reset_llm_provider_cache',
]
