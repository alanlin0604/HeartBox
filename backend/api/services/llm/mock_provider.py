"""Mock LLM provider for tests. Deterministic, no network.

Returns fixed responses keyed off substrings in the system prompt so tests can
assert "given system prompt X, provider returns Y" without spinning up a real
model.
"""
from __future__ import annotations

from typing import Literal

from .base import LLMProvider, LLMProviderError


class MockProvider(LLMProvider):
    """Test-only provider.

    ``is_configured()`` mirrors RemoteTAIDEProvider's contract: needs an
    explicit positive signal to act as "configured". Tests that want to
    exercise the "no LLM available, fall back to local keyword analysis"
    path should set ``LLM_MOCK_CONFIGURED=False`` via override_settings.
    Default is ``True`` so unit tests get deterministic AI behaviour
    out of the box.
    """

    name = 'mock'

    def is_configured(self) -> bool:
        from django.conf import settings
        return bool(getattr(settings, 'LLM_MOCK_CONFIGURED', True))

    def supports_vision(self) -> bool:
        return True

    def chat(self, *, system: str, user: str, **_kwargs) -> str:
        # Tone-aware canned responses so existing 115 tests don't surprise.
        if 'JSON' in system or 'json' in system:
            # The caller probably wanted chat_json. Give them a parseable shape
            # to avoid an exception inside ai_engine.
            return '{"sentiment_score": 0.0, "stress_index": 5}'
        return '[mock-chat] 這是測試用的回覆，內容會根據你的日記提供合適的關懷。'

    def chat_messages(self, *, messages: list[dict], **_kwargs) -> str:
        # Fish out the last user message for a vaguely contextual echo.
        last_user = next(
            (m.get('content', '') for m in reversed(messages) if m.get('role') == 'user'),
            '',
        )
        if isinstance(last_user, list):
            # Multimodal content blocks — just join text parts.
            last_user = ' '.join(
                blk.get('text', '') for blk in last_user if blk.get('type') == 'text'
            )
        return f'[mock-chat-messages] 收到你的話了：{str(last_user)[:60]}'

    def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str | None = None,
        **_kwargs,
    ) -> dict:
        # Recognise sentiment-analysis prompts and return a valid shape.
        if 'sentiment_score' in (schema_hint or '') or 'sentiment_score' in system:
            return {'sentiment_score': 0.0, 'stress_index': 5}
        return {'mock': True, 'system_preview': system[:60]}

    def vision(
        self,
        *,
        system: str,
        user_text: str,
        image_urls: list[str],
        response_format: Literal['text', 'json'] = 'text',
        **_kwargs,
    ) -> dict | str:
        if response_format == 'json':
            return {'sentiment_score': 0.0, 'stress_index': 5}
        return f'[mock-vision] 觀察到 {len(image_urls)} 張圖片。'
