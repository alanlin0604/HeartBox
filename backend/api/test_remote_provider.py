"""Unit tests for ``api.services.llm.remote_provider.RemoteTAIDEProvider``.

Focus: the ``_post_chat`` error-wrapping contract. Every failure mode
that can come out of httpx — TimeoutException, HTTPStatusError,
HTTPError (connect / read), and parse errors from a malformed
upstream response — MUST be wrapped as ``LLMProviderError`` so callers
only need to handle one exception class.

The adversarial review specifically flagged ``AttributeError`` and
``TypeError`` from a server returning an unexpected shape (e.g. a list
instead of a dict). Those are pinned here.

Pure-Python (no Django setUp, no DB, no network). Uses ``unittest.mock``
to swap out ``httpx.Client.post`` with side-effects.

Run with:
    python manage.py test api.test_remote_provider
"""
import unittest
from unittest.mock import MagicMock, patch

import httpx

from api.services.llm.base import LLMProviderError
from api.services.llm.remote_provider import RemoteTAIDEProvider


def _make_provider(api_key='test-key', base_url='https://llm.example.com'):
    return RemoteTAIDEProvider(
        base_url=base_url,
        api_key=api_key,
        chat_model='taide-lx-7b-chat',
        vision_model='llava-v1.6-mistral-7b',
        timeout_s=2.0,
    )


def _ok_response(payload):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    resp.status_code = 200
    resp.text = ''
    return resp


class TestRemoteProviderConfig(unittest.TestCase):

    def test_is_configured_requires_both_url_and_key(self):
        # Both present → True
        self.assertTrue(_make_provider().is_configured())
        # Missing key → False
        self.assertFalse(_make_provider(api_key='').is_configured())
        # Missing url → False
        self.assertFalse(_make_provider(base_url='').is_configured())
        # Both missing → False
        self.assertFalse(_make_provider(api_key='', base_url='').is_configured())

    def test_api_key_set_in_headers(self):
        p = _make_provider(api_key='secret123')
        headers = p._headers()
        self.assertEqual(headers.get('X-API-Key'), 'secret123')

    def test_no_api_key_means_no_header(self):
        p = _make_provider(api_key='')
        headers = p._headers()
        self.assertNotIn('X-API-Key', headers)

    def test_supports_vision_true(self):
        self.assertTrue(_make_provider().supports_vision())

    def test_unconfigured_chat_raises_without_post(self):
        p = _make_provider(api_key='')
        with patch.object(p._client, 'post') as mock_post:
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('not configured', str(ctx.exception).lower())
            mock_post.assert_not_called()


class TestRemoteProviderHappyPath(unittest.TestCase):

    def test_chat_success(self):
        p = _make_provider()
        with patch.object(p._client, 'post') as mock_post:
            mock_post.return_value = _ok_response({
                'choices': [{'message': {'content': '你好！今天天氣不錯。'}}]
            })
            out = p.chat(system='你是助手', user='hi')
            self.assertEqual(out, '你好！今天天氣不錯。')
            # Verify the POST was made with the right shape.
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get('json') or call_kwargs.args[1]
            self.assertEqual(payload['model'], 'taide-lx-7b-chat')
            self.assertEqual(payload['stream'], False)

    def test_chat_messages_passes_history(self):
        p = _make_provider()
        with patch.object(p._client, 'post') as mock_post:
            mock_post.return_value = _ok_response({
                'choices': [{'message': {'content': 'response'}}]
            })
            msgs = [
                {'role': 'system', 'content': 'sys'},
                {'role': 'user', 'content': 'q1'},
                {'role': 'assistant', 'content': 'a1'},
                {'role': 'user', 'content': 'q2'},
            ]
            p.chat_messages(messages=msgs)
            payload = mock_post.call_args.kwargs.get('json') or mock_post.call_args.args[1]
            self.assertEqual(payload['messages'], msgs)


class TestRemoteProviderErrorWrapping(unittest.TestCase):
    """Every failure mode coming out of ``_post_chat`` MUST surface as
    ``LLMProviderError``, never a raw httpx / KeyError / TypeError."""

    def test_timeout_wrapped(self):
        p = _make_provider()
        with patch.object(p._client, 'post', side_effect=httpx.TimeoutException('boom')):
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('timeout', str(ctx.exception).lower())

    def test_http_status_error_wrapped(self):
        p = _make_provider()
        bad_response = MagicMock(spec=httpx.Response)
        bad_response.status_code = 500
        bad_response.text = 'internal server error'
        err = httpx.HTTPStatusError(
            'server error', request=MagicMock(), response=bad_response,
        )
        ok_response = MagicMock(spec=httpx.Response)
        ok_response.raise_for_status.side_effect = err
        ok_response.status_code = 500
        ok_response.text = 'internal server error'
        with patch.object(p._client, 'post', return_value=ok_response):
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('HTTP 500', str(ctx.exception))

    def test_connection_error_wrapped(self):
        """httpx.ConnectError is a subclass of HTTPError — must be
        wrapped by the general HTTPError except clause."""
        p = _make_provider()
        with patch.object(p._client, 'post', side_effect=httpx.ConnectError('refused')):
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('network', str(ctx.exception).lower())

    def test_malformed_choices_key_missing(self):
        """Server returned ``{}`` with no ``choices`` field — the
        ``data.get('choices') or [{}]`` chain returns ``[{}]`` → first
        item has no ``message`` → empty string → 'empty response' raise."""
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response({})):
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('empty', str(ctx.exception).lower())

    def test_choices_is_list_of_strings_not_dicts(self):
        """Server returned ``{'choices': ['just a string']}`` — strings
        don't have ``.get(...)``. This is the AttributeError case the
        review specifically called out."""
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response({
            'choices': ['not-a-dict']
        })):
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('parse', str(ctx.exception).lower())

    def test_choices_is_not_a_list(self):
        """Server returned ``{'choices': 'not a list'}`` — subscripting
        a string with [0] returns a char, .get fails. TypeError case."""
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response({
            'choices': 'whoops'
        })):
            with self.assertRaises(LLMProviderError):
                p.chat(system='s', user='u')

    def test_data_is_not_a_dict(self):
        """Server returned a list at top level instead of a dict.
        ``data.get(...)`` raises AttributeError."""
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response(['a', 'b'])):
            with self.assertRaises(LLMProviderError):
                p.chat(system='s', user='u')

    def test_empty_content_string(self):
        """Server returned a valid shape but content is empty string —
        treat as failure (empty reply is not useful)."""
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response({
            'choices': [{'message': {'content': ''}}]
        })):
            with self.assertRaises(LLMProviderError) as ctx:
                p.chat(system='s', user='u')
            self.assertIn('empty', str(ctx.exception).lower())

    def test_content_is_not_a_string(self):
        """Server returned content as a list of blocks (multimodal shape
        that we don't expect for chat). Treat as parse failure."""
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response({
            'choices': [{'message': {'content': [{'type': 'text', 'text': 'x'}]}}]
        })):
            with self.assertRaises(LLMProviderError):
                p.chat(system='s', user='u')


class TestRemoteProviderChatJson(unittest.TestCase):

    def test_chat_json_appends_schema_hint_to_system(self):
        p = _make_provider()
        with patch.object(p._client, 'post') as mock_post:
            mock_post.return_value = _ok_response({
                'choices': [{'message': {'content': '{"a": 1}'}}]
            })
            p.chat_json(system='base', user='u', schema_hint='{a: int}')
            payload = mock_post.call_args.kwargs.get('json') or mock_post.call_args.args[1]
            sys_msg = payload['messages'][0]['content']
            self.assertIn('base', sys_msg)
            self.assertIn('{a: int}', sys_msg)
            self.assertIn('JSON', sys_msg)

    def test_chat_json_parses_via_tolerant_parser(self):
        p = _make_provider()
        with patch.object(p._client, 'post', return_value=_ok_response({
            'choices': [{'message': {'content': 'Sure: {"sentiment": 0.5}'}}]
        })):
            out = p.chat_json(system='s', user='u')
            self.assertEqual(out, {'sentiment': 0.5})


if __name__ == '__main__':
    unittest.main()
