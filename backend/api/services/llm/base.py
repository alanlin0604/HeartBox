"""Abstract base for LLM providers + tolerant JSON parser.

Every concrete provider (RemoteTAIDE, Mock, OpenAI legacy) inherits ``LLMProvider``
and raises ``LLMProviderError`` on any failure (network, HTTP 5xx, JSON parse,
empty response). Callers only need to handle that one exception class plus the
usual ``Exception`` for true catastrophes.

The message format mirrors OpenAI's chat-completions schema so that fronting a
TAIDE deployment with vLLM's OpenAI-compatible server requires no adapter.
"""
from __future__ import annotations

import abc
import json
import re
from typing import Literal


class LLMProviderError(Exception):
    """Single exception class callers should catch. Wraps timeouts, HTTP errors,
    parse failures, empty responses, etc."""


class LLMProvider(abc.ABC):
    """ABC for chat-style LLM backends.

    Method shape is fixed across providers so callers don't branch on backend.
    Concrete providers may raise ``LLMProviderError`` from any method.
    """

    name: str = 'unknown'

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider can serve a request right now (URL/key set)."""

    def supports_vision(self) -> bool:
        """Subclasses override if they can actually call a vision model."""
        return False

    @abc.abstractmethod
    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float | None = None,
    ) -> str:
        """Single-turn chat. Returns plain text. Raises ``LLMProviderError``."""

    @abc.abstractmethod
    def chat_messages(
        self,
        *,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float | None = None,
    ) -> str:
        """Multi-turn chat with explicit message history.

        ``messages`` follows OpenAI's schema: list of ``{'role': ..., 'content': ...}``.
        """

    @abc.abstractmethod
    def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 200,
        timeout: float | None = None,
    ) -> dict:
        """Single-turn chat constrained to JSON output. Returns parsed dict.

        Raises ``LLMProviderError`` if the model output cannot be coerced to JSON.
        ``schema_hint`` (optional) is appended to the system prompt to nudge the
        model toward the right shape — small local models need this more than
        gpt-4o-mini did.
        """

    def vision(
        self,
        *,
        system: str,
        user_text: str,
        image_urls: list[str],
        response_format: Literal['text', 'json'] = 'text',
        temperature: float = 0.7,
        max_tokens: int = 300,
        max_images: int = 3,
        image_detail: str = 'low',
        timeout: float | None = None,
    ) -> dict | str:
        """Multimodal call. Default implementation raises so non-vision providers
        don't need to override."""
        raise LLMProviderError(f'{self.name} does not support vision')

    # ------------------------------------------------------------------
    # Tolerant JSON parsing — shared across all providers because small
    # local models love to add markdown fences or trailing commentary.
    # ------------------------------------------------------------------
    @staticmethod
    def parse_json_tolerant(raw: str) -> dict:
        """Extract a JSON object from a model response that may contain
        markdown fences, prose, or trailing text.

        Strategy:
          1. Strip markdown ``` fences if present.
          2. If the whole thing parses as JSON, return it.
          3. Otherwise find the first balanced ``{ ... }`` substring and parse that.

        Raises ``LLMProviderError`` if no JSON object can be extracted.
        """
        if not raw:
            raise LLMProviderError('empty response')

        text = raw.strip()
        # Strip ```json ... ``` or ``` ... ```
        if text.startswith('```'):
            # drop first line (``` or ```json) and trailing ```
            after_first_newline = text.split('\n', 1)
            if len(after_first_newline) == 2:
                text = after_first_newline[1]
            text = text.rsplit('```', 1)[0].strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, json.JSONDecodeError):
            pass

        # Fallback: find first balanced { ... }
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, json.JSONDecodeError) as e:
                raise LLMProviderError(f'JSON extracted but failed to parse: {e}') from e

        raise LLMProviderError(f'no JSON object found in response: {raw[:120]!r}')
