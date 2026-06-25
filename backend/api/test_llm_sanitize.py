"""Unit tests for api.services.llm.sanitize.

Regression suite for the prompt-template leak bug (workflow audit
wf_ba1ab074-010): when llm_server/engine.py used a string-prefix strip
instead of a token-id slice, the entire chat template (system + user +
assistant wrapper) was returned to consumers, who then persisted it to
DB and rendered it to UI. ``scrub_llm_output`` is the defense-in-depth
layer that runs at the ``remote_provider`` chokepoint plus every consumer,
so even a future regression of the engine fix never reaches users.
"""
from django.test import SimpleTestCase

from api.services.llm.sanitize import (
    MAX_LLM_TEXT_CHARS,
    detect_system_echo,
    scrub_llm_output,
)


class ScrubLLMOutputTests(SimpleTestCase):
    """Verify scrub_llm_output strips every known template marker shape."""

    def test_inst_and_sys_markers_stripped(self):
        # Llama-2 / TAIDE wrapping shape that the workflow audit traced
        # leaking to both the daily-prompt card and the AI feedback card.
        leaked = (
            '[INST] <<SYS>>You are a helpful assistant<</SYS>> '
            'what is 1+1 [/INST]\nassistant: 2'
        )
        out = scrub_llm_output(leaked)
        # Whitespace between cleaned chunks can vary by one space, but no
        # template markers and no role prefix may survive.
        for forbidden in ('[INST]', '[/INST]', '<<SYS>>', '<</SYS>>', 'assistant:'):
            self.assertNotIn(forbidden, out)
        for word in ('You are a helpful assistant', 'what is 1+1', '2'):
            self.assertIn(word, out)

    def test_strips_inst_in_any_order(self):
        # E_INST before B_INST + BOS/EOS bracketing — observed when small
        # models hallucinate the format halfway through a real reply.
        out = scrub_llm_output('[/INST] foo [INST]<<SYS>>x<</SYS>></s>')
        self.assertNotIn('[INST]', out)
        self.assertNotIn('[/INST]', out)
        self.assertNotIn('<<SYS>>', out)
        self.assertNotIn('</s>', out)
        self.assertIn('foo', out)
        self.assertIn('x', out)

    def test_chinese_role_prefix_full_width_colon(self):
        # 助理：... is the most common parrot shape from TAIDE.
        self.assertEqual(scrub_llm_output('助理：我聽到你說的'), '我聽到你說的')

    def test_qwen_im_tokens_stripped(self):
        leaked = '<|im_start|>assistant\nhello<|im_end|>'
        self.assertEqual(scrub_llm_output(leaked), 'hello')

    def test_llama3_special_tokens_stripped(self):
        leaked = (
            '<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n'
            'hi<|eot_id|><|start_header_id|>assistant<|end_header_id|>\nhi back'
        )
        out = scrub_llm_output(leaked)
        self.assertNotIn('<|', out)
        self.assertIn('hi back', out)

    def test_llava_image_placeholder_stripped(self):
        self.assertEqual(scrub_llm_output('<image> a cat'), 'a cat')

    def test_stacked_role_prefixes_unwound(self):
        # Up to 4 nested prefixes should peel cleanly.
        out = scrub_llm_output('assistant: user: system: actual reply')
        self.assertEqual(out, 'actual reply')

    def test_empty_and_none_safe(self):
        self.assertEqual(scrub_llm_output(''), '')
        self.assertEqual(scrub_llm_output(None), '')
        self.assertEqual(scrub_llm_output('   '), '')

    def test_idempotent(self):
        raw = '[INST] <<SYS>>hi<</SYS>> hello [/INST] assistant: 答案是 42'
        once = scrub_llm_output(raw)
        twice = scrub_llm_output(once)
        self.assertEqual(once, twice)

    def test_hotline_string_preserved(self):
        # CrisisGuard.prepend_hotline runs AFTER scrub; verify scrub doesn't
        # eat the canonical 1925 hotline number or surrounding prose.
        text = '如有自傷想法請撥 1925（24小時免費）\n你今天還好嗎？'
        self.assertEqual(scrub_llm_output(text), text)

    def test_collapses_excess_newlines(self):
        out = scrub_llm_output('a\n\n\n\n\nb')
        self.assertEqual(out, 'a\n\nb')

    def test_strips_control_bytes(self):
        out = scrub_llm_output('hello\x00\x01world')
        self.assertEqual(out, 'helloworld')

    def test_preserves_tabs_and_newlines(self):
        self.assertEqual(scrub_llm_output('a\tb\nc'), 'a\tb\nc')

    def test_hard_caps_runaway_length(self):
        runaway = 'x' * (MAX_LLM_TEXT_CHARS + 500)
        out = scrub_llm_output(runaway)
        self.assertLessEqual(len(out), MAX_LLM_TEXT_CHARS)

    def test_real_taide_leak_from_screenshot(self):
        # Verbatim shape from the user's screenshot — the bug we're fixing.
        leaked = (
            '[INST] <<SYS>>你是一位溫暖、專業的心理健康顧問。<</SYS>>\n'
            '日記內容：「<p>今天工作壓力很大很沮喪</p>」 [/INST] '
            '親愛的，看到你今天感到如此辛苦與沮喪'
        )
        out = scrub_llm_output(leaked)
        self.assertNotIn('[INST]', out)
        self.assertNotIn('[/INST]', out)
        self.assertNotIn('<<SYS>>', out)
        # The actual reply must survive.
        self.assertIn('親愛的', out)
        self.assertIn('沮喪', out)


class DetectSystemEchoTests(SimpleTestCase):
    """Verify detect_system_echo recognises verbatim prompt parroting."""

    SYSTEM = (
        '你是一位溫暖、專業的心理健康夥伴，名叫「小心」。'
        '你具備心理諮商的基礎知識，能以同理心傾聽使用者的心事。'
    )

    def test_full_system_substring_detected(self):
        echoed = self.SYSTEM[:80] + ' tail text'
        self.assertTrue(detect_system_echo(echoed, self.SYSTEM))

    def test_unrelated_reply_not_flagged(self):
        self.assertFalse(detect_system_echo(
            '我聽到你說的了，能多告訴我一些嗎？', self.SYSTEM,
        ))

    def test_short_system_returns_false(self):
        # 39 chars system, threshold 40 → can't possibly echo, defensive.
        self.assertFalse(detect_system_echo('long enough reply text here', 'a' * 39))

    def test_empty_inputs_safe(self):
        self.assertFalse(detect_system_echo('', self.SYSTEM))
        self.assertFalse(detect_system_echo('reply', ''))
        self.assertFalse(detect_system_echo(None, self.SYSTEM))

    def test_whitespace_normalised_for_matching(self):
        # Model echoes system but inserts newlines/indent. Should still match
        # because both strings are whitespace-stripped before comparison.
        echoed = self.SYSTEM[:60].replace('，', '，\n  ').replace('。', '。\n')
        self.assertTrue(detect_system_echo(echoed, self.SYSTEM))
