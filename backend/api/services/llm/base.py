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
        larger hosted models do.
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
    def _first_balanced_json_object(text: str) -> str | None:
        """Return the substring of the FIRST balanced ``{ ... }`` block, or
        None. Walks the text once, tracks brace depth, and respects
        backslash-escaped quotes inside strings — so multi-object output
        like ``{ "a": 1 }\\n{ "b": 2 }`` returns just ``{ "a": 1 }`` instead
        of ``re.search(r'\\{[\\s\\S]*\\}')`` greedily swallowing both into a
        single unparseable blob."""
        start = text.find('{')
        if start < 0:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if in_string:
                if c == '\\':
                    escape = True
                elif c == '"':
                    in_string = False
                continue
            if c == '"':
                in_string = True
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

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

        # Fallback: find first balanced { ... } using a brace-depth walker
        # rather than a greedy regex (which would swallow trailing prose).
        candidate = LLMProvider._first_balanced_json_object(text)
        if candidate:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, json.JSONDecodeError) as e:
                raise LLMProviderError(f'JSON extracted but failed to parse: {e}') from e

        raise LLMProviderError(f'no JSON object found in response: {raw[:120]!r}')
