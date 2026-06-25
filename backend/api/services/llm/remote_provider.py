"""Talks to the local FastAPI inference server (TAIDE + LLaVA).

The remote server speaks an OpenAI-compatible JSON shape:

    POST /v1/chat/completions
    Headers: X-API-Key: <key>
    Body: { "model": "...", "messages": [...], "temperature": ..., "max_tokens": ... }

Designed for ``LLM_PROVIDER=remote_taide``. All errors (network, HTTP 4xx/5xx,
parse) are normalised to ``LLMProviderError``.

Thread safety: ``httpx.Client`` is documented thread-safe, so the single
``self._client`` instance is shared across background threads (e.g. the
``threading.Thread`` workers in ``views/notes.py``).
"""
from __future__ import annotations

import logging
import time
from typing import Literal

from .base import LLMProvider, LLMProviderError
from .sanitize import scrub_llm_output

logger = logging.getLogger(__name__)

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:  # pragma: no cover - httpx is a hard dep but graceful
    _HAS_HTTPX = False


class RemoteTAIDEProvider(LLMProvider):
    name = 'remote_taide'

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = '',
        chat_model: str = 'taide-lx-7b-chat',
        vision_model: str = 'llava-v1.6-mistral-7b',
        timeout_s: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.chat_model = chat_model
        self.vision_model = vision_model
        self.default_timeout = timeout_s

        if not _HAS_HTTPX:
            raise LLMProviderError(
                'httpx not installed. Add httpx==0.28.1 to backend requirements.'
            )

        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_s, connect=10.0),
            headers=self._headers(),
        )

    def _headers(self) -> dict:
        h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.api_key:
            h['X-API-Key'] = self.api_key
        return h

    def is_configured(self) -> bool:
        # Both URL AND API key required. Empty URL = no deployment yet.
        # Empty API key = misconfigured (we never want to call a public tunnel
        # without auth). Returning False here makes _get_llm_provider_or_none()
        # short-circuit to fallback without paying a connect timeout.
        return bool(self.base_url and self.api_key)

    def supports_vision(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Low-level POST with structured logging + error normalisation.
    # ------------------------------------------------------------------
    def _post_chat(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None,
        op: str,
    ) -> str:
        if not self.is_configured():
            raise LLMProviderError('LLM_SERVER_URL not configured')

        url = f'{self.base_url}/v1/chat/completions'
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False,
        }
        t0 = time.monotonic()
        status = 'ok'
        try:
            resp = self._client.post(
                url,
                json=payload,
                timeout=timeout or self.default_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
            if not isinstance(text, str) or not text:
                status = 'error'
                raise LLMProviderError(f'empty response from {model}')
            # Defense-in-depth scrub: even if the upstream llm_server engine
            # regresses and leaks [INST] / <<SYS>> / role markers, they never
            # reach the DB / cache / UI. See sanitize.py for the marker set.
            cleaned = scrub_llm_output(text)
            if cleaned != text:
                logger.warning(
                    'llm_template_leak provider=%s op=%s model=%s removed_chars=%d',
                    self.name, op, model, len(text) - len(cleaned),
                    extra={'llm_provider': self.name, 'llm_op': op,
                           'llm_model': model, 'llm_event': 'template_leak'},
                )
            if not cleaned:
                status = 'error'
                raise LLMProviderError(
                    f'empty response after sanitization from {model} '
                    f'(raw was {len(text)} chars of template-only)'
                )
            return cleaned
        except httpx.TimeoutException as e:
            status = 'timeout'
            raise LLMProviderError(f'timeout calling {model}: {e}') from e
        except httpx.HTTPStatusError as e:
            status = f'http_{e.response.status_code}'
            body = e.response.text[:200] if e.response is not None else ''
            raise LLMProviderError(
                f'HTTP {e.response.status_code} from {model}: {body}'
            ) from e
        except httpx.HTTPError as e:
            status = 'network'
            raise LLMProviderError(f'network error calling {model}: {e}') from e
        except (ValueError, KeyError, AttributeError, TypeError) as e:
            # AttributeError / TypeError: server returned an unexpected shape
            # (e.g. ``data`` is a list, or ``choices[0]`` is a string), and
            # the chained ``.get(...)`` blew up. Treat the same as parse error
            # so callers only ever have to handle LLMProviderError.
            status = 'parse'
            raise LLMProviderError(f'parse error from {model}: {e}') from e
        finally:
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                'llm_call provider=%s op=%s model=%s latency_ms=%d status=%s',
                self.name, op, model, latency_ms, status,
                extra={
                    'llm_provider': self.name,
                    'llm_op': op,
                    'llm_model': model,
                    'llm_latency_ms': latency_ms,
                    'llm_status': status,
                },
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float | None = None,
    ) -> str:
        messages = [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ]
        return self._post_chat(
            messages=messages,
            model=self.chat_model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            op='chat',
        )

    def chat_messages(
        self,
        *,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float | None = None,
    ) -> str:
        return self._post_chat(
            messages=messages,
            model=self.chat_model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            op='chat_messages',
        )

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
        # Append schema hint to nudge small models. TAIDE-LX-7B is less reliable
        # at JSON than larger hosted models, so we double down on the instruction.
        sys_with_hint = system
        if schema_hint:
            sys_with_hint = (
                f'{system}\n\n'
                f'你必須只回傳一個 JSON 物件，符合此 schema: {schema_hint}\n'
                '不要回傳 markdown 程式碼框、解釋文字、前置詞 — 只有 JSON。'
            )
        messages = [
            {'role': 'system', 'content': sys_with_hint},
            {'role': 'user', 'content': user},
        ]
        raw = self._post_chat(
            messages=messages,
            model=self.chat_model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            op='chat_json',
        )
        return self.parse_json_tolerant(raw)

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
        content_blocks: list[dict] = [{'type': 'text', 'text': user_text}]
        for url in image_urls[:max_images]:
            content_blocks.append({
                'type': 'image_url',
                'image_url': {'url': url, 'detail': image_detail},
            })

        sys = system
        if response_format == 'json':
            sys = (
                f'{system}\n\n'
                '你必須只回傳一個 JSON 物件。不要 markdown、不要解釋。'
            )

        messages = [
            {'role': 'system', 'content': sys},
            {'role': 'user', 'content': content_blocks},
        ]
        raw = self._post_chat(
            messages=messages,
            model=self.vision_model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout or max(self.default_timeout, 120.0),  # vision swap is slow
            op='vision',
        )
        if response_format == 'json':
            return self.parse_json_tolerant(raw)
        return raw
