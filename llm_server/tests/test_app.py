"""Integration tests for llm_server's FastAPI app + helpers.

Focus: middleware ordering (auth must run BEFORE body parse), body-size
limits, /health unauth surface, CORS-on-401, and the SSRF / image-fetch
helpers. The HF model is NEVER loaded — we stub the engine's loader so
TestClient can exercise the wire-format without touching the GPU.

Run from the repo root (the backend venv has fastapi installed):

    backend/venv/Scripts/python.exe -m pytest llm_server/tests/ -v

If pytest is not available, ``python -m unittest discover llm_server.tests``
also works — the file is written in a pytest+unittest-compatible style.
"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from llm_server.config import Settings
from llm_server import main as main_module
from llm_server import engine as engine_module


def _make_settings() -> Settings:
    return Settings(
        api_key='test-key-' + 'a' * 56,         # 64 chars total
        autoload_on_startup=False,              # do NOT load HF weights
        bnb_disable=True,                       # tests run on CPU dev boxes
        cors_allow_origins='https://example.com',
        body_limit_bytes=100_000,
        request_timeout_s=2,
    )


def _make_app_and_client():
    """Build a TestClient with the inference loader stubbed out so no GPU
    or HF model is required. The client is a context manager so lifespan
    startup/shutdown actually fire."""
    settings = _make_settings()

    # Stub both atomic loaders so swap_to() returns sentinels rather than
    # trying to load a 7B model into VRAM.
    def fake_load_taide_inner(self):
        return (object(), object(), None, 'taide')

    def fake_load_llava_inner(self):
        return (object(), object(), object(), 'llava')

    with patch.object(engine_module.InferenceEngine, '_load_taide_inner', fake_load_taide_inner), \
         patch.object(engine_module.InferenceEngine, '_load_llava_inner', fake_load_llava_inner):
        app = main_module.create_app(settings)
        client = TestClient(app)
        client.__enter__()
        return client, settings


# ======================================================================
# /health surface
# ======================================================================
class HealthTests(unittest.TestCase):
    def setUp(self):
        self.client, self.settings = _make_app_and_client()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_health_no_auth_required(self):
        r = self.client.get('/health')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'status': 'ok'})

    def test_health_does_not_leak_model_ids(self):
        """Phase 0b second-pass review: /health is unauth and must not
        leak ``taide_model`` / ``llava_model`` / ``current_model`` to an
        attacker fingerprinting the deployment."""
        body = self.client.get('/health').json()
        for forbidden in ('taide_model', 'llava_model', 'current_model'):
            self.assertNotIn(forbidden, body, f'/health leaked {forbidden}')


# ======================================================================
# Auth middleware — must run BEFORE Pydantic body parse.
# ======================================================================
class AuthOrderingTests(unittest.TestCase):
    def setUp(self):
        self.client, self.settings = _make_app_and_client()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_chat_without_key_returns_401(self):
        r = self.client.post(
            '/v1/chat/completions',
            json={'messages': [{'role': 'user', 'content': 'hi'}]},
        )
        self.assertEqual(r.status_code, 401)

    def test_chat_with_wrong_key_returns_401(self):
        r = self.client.post(
            '/v1/chat/completions',
            headers={'X-API-Key': 'wrong-key'},
            json={'messages': [{'role': 'user', 'content': 'hi'}]},
        )
        self.assertEqual(r.status_code, 401)

    def test_auth_runs_before_body_parse(self):
        """Critical security property: an unauth POST with MALFORMED
        JSON must return 401 (auth rejected first), NOT 422 (Pydantic
        parse rejected). Otherwise an attacker could DoS us by sending
        many large invalid bodies that all get parsed before auth fires."""
        r = self.client.post(
            '/v1/chat/completions',
            data='{"messages": [malformed-body-here',
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(
            r.status_code, 401,
            f'auth must run before body parse, got {r.status_code}',
        )


# ======================================================================
# Body-size middleware — chunked rejected, CL enforced.
# ======================================================================
class BodyLimitTests(unittest.TestCase):
    def setUp(self):
        self.client, self.settings = _make_app_and_client()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_body_too_large_returns_413(self):
        big_payload = '{"messages": [{"role":"user","content":"' + ('x' * 200_000) + '"}]}'
        r = self.client.post(
            '/v1/chat/completions',
            headers={'X-API-Key': self.settings.api_key},
            data=big_payload,
        )
        self.assertEqual(r.status_code, 413)

    def test_chunked_transfer_encoding_rejected(self):
        """``Transfer-Encoding: chunked`` previously bypassed the
        Content-Length cap. Must now 411."""
        r = self.client.post(
            '/v1/chat/completions',
            headers={
                'X-API-Key': self.settings.api_key,
                'Transfer-Encoding': 'chunked',
            },
            data='{"messages": []}',
        )
        # TestClient sometimes rewrites TE; accept either 411 or 400 but
        # MUST NOT be a 2xx success and MUST NOT be a 422 (which would
        # mean the body was parsed despite chunked).
        self.assertIn(r.status_code, (411, 400),
                      f'chunked must be rejected at middleware, got {r.status_code}')


# ======================================================================
# CORS on 401 — middleware ordering review finding.
# ======================================================================
class CorsTests(unittest.TestCase):
    def setUp(self):
        self.client, self.settings = _make_app_and_client()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_401_response_carries_cors_headers(self):
        """Second-pass review: if CORS is added BEFORE auth, a browser
        client with a bad key sees a CORS error instead of the real 401.
        CORS must wrap the auth middleware so even 401s carry ACAO."""
        r = self.client.post(
            '/v1/chat/completions',
            headers={'Origin': 'https://example.com'},
            json={'messages': [{'role': 'user', 'content': 'hi'}]},
        )
        self.assertEqual(r.status_code, 401)
        lower_headers = {k.lower() for k in r.headers}
        self.assertIn(
            'access-control-allow-origin', lower_headers,
            '401 response is missing ACAO header — CORS middleware is '
            'INSIDE auth and a browser client will see a CORS error '
            'instead of the API-key error',
        )


# ======================================================================
# SSRF helpers — _resolve_safe_ips and _verify_peer_ip
# ======================================================================
class SsrfHelperTests(unittest.TestCase):
    def test_empty_host_rejected(self):
        with self.assertRaisesRegex(ValueError, 'empty host'):
            main_module._resolve_safe_ips('')

    def test_localhost_rejected(self):
        # 'localhost' resolves to 127.0.0.1 / ::1 on every platform.
        with self.assertRaisesRegex(ValueError, 'non-public'):
            main_module._resolve_safe_ips('localhost')

    def test_invalid_host_rejected(self):
        # Use an obviously unresolvable name.
        with self.assertRaisesRegex(ValueError, 'dns resolution failed'):
            main_module._resolve_safe_ips('this-host-does-not-exist.invalid.tld.example.local')

    def test_verify_peer_ip_fails_closed_when_stream_missing(self):
        """If response.extensions has no network_stream, _verify_peer_ip
        must REJECT (fail-closed) rather than silently let the SSRF
        rebind through. Second-pass review caught the original code
        silently returning None here."""
        class _Resp:
            extensions = {}
        with self.assertRaisesRegex(ValueError, 'cannot verify peer IP'):
            main_module._verify_peer_ip(_Resp(), {'1.2.3.4'}, 'example.com')

    def test_verify_peer_ip_rejects_mismatch(self):
        """If the actual TCP peer is NOT in the pre-validated safe set
        (the DNS-rebinding case), reject."""
        class _Stream:
            def get_extra_info(self, key):
                if key == 'server_addr':
                    return ('127.0.0.1', 80)
                return None
        class _Resp:
            extensions = {'network_stream': _Stream()}
        with self.assertRaisesRegex(ValueError, 'rebind detected'):
            main_module._verify_peer_ip(_Resp(), {'1.2.3.4'}, 'evil.example.com')

    def test_verify_peer_ip_accepts_match(self):
        class _Stream:
            def get_extra_info(self, key):
                if key == 'server_addr':
                    return ('1.2.3.4', 443)
                return None
        class _Resp:
            extensions = {'network_stream': _Stream()}
        # Should not raise.
        main_module._verify_peer_ip(_Resp(), {'1.2.3.4', '5.6.7.8'}, 'example.com')


# ======================================================================
# _fetch_images URL scheme guard
# ======================================================================
class FetchImagesUrlGuardTests(unittest.TestCase):
    def test_non_http_scheme_rejected(self):
        async def run():
            try:
                await main_module._fetch_images(['file:///etc/passwd'])
                return None
            except ValueError as e:
                return str(e)
        msg = asyncio.run(run())
        self.assertIsNotNone(msg)
        self.assertIn('non-http', msg)

    def test_empty_list_returns_empty(self):
        result = asyncio.run(main_module._fetch_images([]))
        self.assertEqual(result, [])


# ======================================================================
# _ensure_image_blocks normalization (used by /v1/vision route)
# ======================================================================
class EnsureImageBlocksTests(unittest.TestCase):
    """Verifies the helper that injects <image> placeholders into LLaVA
    prompts. Module-level helper so we can call directly without spinning
    up TestClient or the engine."""

    def test_empty_urls_noop(self):
        messages = [{'role': 'user', 'content': 'hi'}]
        main_module._ensure_image_blocks(messages, [])
        # No change — content still the plain string.
        self.assertEqual(messages, [{'role': 'user', 'content': 'hi'}])

    def test_string_content_becomes_list_with_image_block(self):
        """The common /v1/vision client shape: string content + separate
        image_urls top-level array. Helper must transform into the
        OpenAI-shaped multipart content the engine's prompt builder
        expects."""
        messages = [{'role': 'user', 'content': 'describe this'}]
        main_module._ensure_image_blocks(messages, ['http://x.example/a.jpg'])
        self.assertEqual(len(messages), 1)
        content = messages[0]['content']
        self.assertIsInstance(content, list)
        self.assertEqual(content[0], {'type': 'text', 'text': 'describe this'})
        self.assertEqual(content[1], {
            'type': 'image_url',
            'image_url': {'url': 'http://x.example/a.jpg'},
        })

    def test_image_block_appended_to_last_user_message(self):
        """If multiple user messages exist, only the LAST gets the
        image block (per docstring contract)."""
        messages = [
            {'role': 'user', 'content': 'first'},
            {'role': 'assistant', 'content': 'reply'},
            {'role': 'user', 'content': 'second'},
        ]
        main_module._ensure_image_blocks(messages, ['http://x.example/a.jpg'])
        # First user untouched
        self.assertEqual(messages[0]['content'], 'first')
        # Last user transformed
        self.assertIsInstance(messages[2]['content'], list)

    def test_existing_image_blocks_not_duplicated(self):
        """If the caller already wired image_url blocks, the helper must
        be idempotent (don't append duplicates)."""
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'see this'},
                {'type': 'image_url', 'image_url': {'url': 'http://prev.example/a.jpg'}},
            ],
        }]
        main_module._ensure_image_blocks(messages, ['http://new.example/b.jpg'])
        # Existing list preserved as-is.
        self.assertEqual(len(messages[0]['content']), 2)

    def test_creates_user_message_if_none_present(self):
        messages = [{'role': 'system', 'content': 'be helpful'}]
        main_module._ensure_image_blocks(messages, ['http://x.example/a.jpg'])
        # New user message appended.
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[-1]['role'], 'user')


if __name__ == '__main__':
    unittest.main()
