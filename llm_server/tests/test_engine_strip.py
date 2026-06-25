"""Regression tests for the prompt-strip logic in engine.py.

The original bug (workflow audit wf_ba1ab074-010):
  * ``_generate_chat_sync`` decoded the full output_ids and used
    ``full.startswith(prompt)`` to peel the input. ``skip_special_tokens=True``
    removes BOS / <|begin_of_text|> from the decoded text but those bytes
    were never in the source ``prompt`` string, so the prefix check failed
    on Llama-2 / Llama-3 / TAIDE. The fallback ``split('assistant:')[-1]``
    found no match in real chat templates and returned the entire decoded
    text — including the system prompt — to the caller.

The fix slices ``output_ids[0][tokens_in:]`` before decoding, which is the
only correct way to recover the new tokens regardless of template format
or BOS/EOS handling.

These tests use lightweight stubs (no torch tensors required) to verify the
slice arithmetic and decode call order — they intentionally do NOT load a
real model, so they run in seconds on any dev box.
"""
from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock

try:
    import torch
except ImportError:  # pragma: no cover - skip on dev boxes without torch
    torch = None


class _StubTokenizer:
    """Records what slice it was asked to decode."""

    pad_token_id = 0
    eos_token_id = 0

    def __init__(self):
        self.decoded_ids = []
        self.chat_template = '{}'  # presence triggers the apply path

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        # Real templates return a string like '<s>[INST] ... [/INST]'; for
        # the test we just produce a deterministic shape we can count tokens for.
        return '[INST] ' + str(messages) + ' [/INST]'

    def __call__(self, prompt, *, return_tensors, truncation, max_length):
        # Real tokenizer returns BatchEncoding; we only need .input_ids.shape[1]
        # and .to(device). Fake it with a tiny tensor.
        n = max(1, len(prompt) // 4)  # rough token count
        ids = torch.arange(1, n + 1).unsqueeze(0)  # shape [1, n]
        out = MagicMock()
        out.input_ids = ids
        out.to = MagicMock(return_value=out)
        # Make ** unpacking work — generate(**inputs) expects a mapping.
        out.keys = lambda: ['input_ids']
        out.__getitem__ = lambda self_, k: ids if k == 'input_ids' else None
        return out

    def decode(self, ids, *, skip_special_tokens):
        # Record the IDs we were asked to decode so the test can assert.
        self.decoded_ids = list(ids.tolist()) if hasattr(ids, 'tolist') else list(ids)
        # Decode as ASCII letters keyed off id for an inspectable string.
        return ''.join(chr(65 + (i % 26)) for i in self.decoded_ids)


class _StubModel:
    device = torch.device('cpu')

    def __init__(self, *, prompt_len, reply_len):
        self.prompt_len = prompt_len
        self.reply_len = reply_len

    def generate(self, *, input_ids, **kwargs):
        # HF generate() returns [input_ids ++ new_ids]; emulate that.
        new_ids = torch.arange(100, 100 + self.reply_len).unsqueeze(0)
        return torch.cat([input_ids, new_ids], dim=1)


@unittest.skipIf(torch is None, 'torch not installed')
class TestEngineTokenSlice(unittest.TestCase):
    """Verify _generate_chat_sync slices by token count, not by string match."""

    def setUp(self):
        # Import lazily so torch can be skipped on machines without it.
        from llm_server import engine

        self.engine_module = engine

    def _build_engine_with_stubs(self, prompt_len=10, reply_len=5):
        eng = self.engine_module.InferenceEngine(
            taide_model_id='stub/taide', llava_model_id='stub/llava',
            bnb_disable=True,
        )
        tokenizer = _StubTokenizer()
        model = _StubModel(prompt_len=prompt_len, reply_len=reply_len)
        eng._model = model
        eng._tokenizer = tokenizer
        return eng, tokenizer, model

    def test_decode_called_on_new_tokens_only(self):
        eng, tokenizer, _model = self._build_engine_with_stubs(reply_len=7)
        stop = threading.Event()
        reply, tokens_in, tokens_out = eng._generate_chat_sync(
            [{'role': 'user', 'content': 'hi'}],
            temperature=0.0, max_tokens=8, stop_event=stop,
        )
        # tokens_out should be exactly reply_len from the stub model.
        self.assertEqual(tokens_out, 7)
        # decode must have been asked for exactly the post-input slice —
        # NOT the full output_ids. The stub's prompt_len + reply_len means
        # full output has tokens_in + 7 IDs; we want only the last 7.
        self.assertEqual(len(tokenizer.decoded_ids), 7)
        # Stub's new_ids start at 100, so the decoded IDs must be 100..106.
        self.assertEqual(tokenizer.decoded_ids, list(range(100, 107)))

    def test_reply_does_not_contain_prompt_template(self):
        """The whole point of the fix: even with a leaky tokenizer.decode
        round-trip, the reply must not contain template markers from the input.
        """
        eng, tokenizer, _model = self._build_engine_with_stubs(reply_len=4)
        stop = threading.Event()
        reply, _ti, _to = eng._generate_chat_sync(
            [{'role': 'system', 'content': '[INST] secret <<SYS>>'},
             {'role': 'user', 'content': 'hi'}],
            temperature=0.0, max_tokens=8, stop_event=stop,
        )
        # The stub decodes IDs 100..103 into ASCII letters — those should be
        # all that comes back. No template fragment from the system prompt.
        self.assertNotIn('[INST]', reply)
        self.assertNotIn('<<SYS>>', reply)
        self.assertNotIn('secret', reply)


if __name__ == '__main__':
    unittest.main()
