"""Abstract base for LLM providers + tolerant JSON parser.

Every concrete provider (RemoteTAIDE, Mock) inherits ``LLMProvider`` and
raises ``LLMProviderError`` on any failure (network, HTTP 5xx, JSON parse,
empty response). Callers only need to handle that one exception class plus
the usual ``Exception`` for true catastrophes.

The message format mirrors the OpenAI chat-completions JSON shape — but the
actual transport in Phase 0b talks to the self-hosted ``llm_server/``
FastAPI service (no OpenAI vendor involved). The legacy OpenAI provider
was removed at the factory level; see ``factory.py`` for details.
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
    def _balanced_json_objects(text: str, *, max_candidates: int = 5):
        """Yield each top-level balanced ``{ ... }`` substring in ``text``.

        Walks the text once per candidate, tracks brace depth, and respects
        backslash-escaped quotes inside strings. Stops after ``max_candidates``
        to avoid pathological scans on adversarial input.

        Used by ``parse_json_tolerant`` so a small-model preamble that
        contains a literal ``{`` in prose (``"with curly braces in {prose}"``)
        does not permanently latch the parser onto the wrong substring —
        if the first balanced block fails ``json.loads`` we slide past it
        and try the next candidate, then raise only if none parse.
        """
        idx = 0
        yielded = 0
        n = len(text)
        while yielded < max_candidates:
            start = text.find('{', idx)
            if start < 0:
                return
            depth = 0
            in_string = False
            escape = False
            end = -1
            for i in range(start, n):
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
                        end = i
                        break
            if end < 0:
                return
            yield text[start:end + 1]
            yielded += 1
            idx = end + 1

    @staticmethod
    def _first_balanced_json_object(text: str) -> str | None:
        """Back-compat shim: return only the first balanced substring or None."""
        for candidate in LLMProvider._balanced_json_objects(text, max_candidates=1):
            return candidate
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

        # Fallback: walk text and try each balanced ``{ ... }`` substring
        # until one parses as a dict. Slides past prose-embedded braces
        # like ``Here is the JSON: "with {prose} in it" {actual: 1}``.
        last_err: Exception | None = None
        for candidate in LLMProvider._balanced_json_objects(text):
            try:
                parsed = json.loads(candidate)
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                continue
            if isinstance(parsed, dict):
                return parsed
            # parsed but not a dict (e.g. list at top-level) — keep looking.

        if last_err is not None:
            raise LLMProviderError(
                f'JSON extracted but no candidate parsed: {last_err}'
            ) from last_err
        raise LLMProviderError(f'no JSON object found in response: {raw[:120]!r}')
