"""Pin the Tier-1 / Tier-2 fallback safety invariant: even when the LLM
provider is down or returns garbage, a HIGH-crisis input MUST surface
the locale's hotline number to the user.

This invariant is the entire point of Phase 0b Batch 4 bug #10:
``_generate_personalized_feedback`` could previously fall through to
``_generate_basic_feedback`` on any exception, and the basic feedback
function has no idea about crisis state. A journal entry containing
``我想死`` during a TAIDE outage would silently surface generic
``今天心情看起來...`` template text with no hotline.

The fix introduced ``_basic_feedback_with_crisis_guard``. These tests
pin its contract per-locale so a future refactor cannot regress it
without somebody noticing.

Run with:
    python manage.py test api.test_ai_engine_crisis_failsafe
"""
import unittest

from api.services.ai_engine import AIEngine


class TestBasicFeedbackWithCrisisGuard(unittest.TestCase):

    def setUp(self):
        # AIEngine is a singleton — using the module-level instance is fine,
        # but we re-build to test the helper without singleton state.
        self.engine = AIEngine()

    # ------------------------------------------------------------------
    # HIGH crisis — hotline MUST appear regardless of locale
    # ------------------------------------------------------------------
    def test_zh_high_text_includes_1925(self):
        """Mandarin HIGH crisis → Taiwan hotline."""
        out = self.engine._basic_feedback_with_crisis_guard('我不想活了', -0.9)
        self.assertIn('1925', out,
                      f'zh-TW HIGH must include 1925 hotline. Got: {out[:120]}')

    def test_en_high_text_includes_988(self):
        """English HIGH crisis → US Suicide & Crisis Lifeline."""
        out = self.engine._basic_feedback_with_crisis_guard(
            'I want to kill myself tonight', -0.85,
        )
        self.assertIn('988', out,
                      f'en HIGH must include 988 hotline. Got: {out[:120]}')

    def test_ja_high_text_includes_japanese_hotline(self):
        """Japanese HIGH crisis → よりそいホットライン or いのちの電話."""
        out = self.engine._basic_feedback_with_crisis_guard('死にたい', -0.9)
        # Either of Japan's two listed hotlines is acceptable.
        has_jp_hotline = ('0120-279-338' in out) or ('0570-783-556' in out)
        self.assertTrue(
            has_jp_hotline,
            f'ja HIGH must include 0120-279-338 or 0570-783-556. Got: {out[:120]}',
        )

    def test_killmyself_no_separator_still_triggers_hotline(self):
        """Adversarial regression: the obfuscation pass must catch
        ``killmyself`` (no separator) and route to the hotline. The
        chain runs CrisisGuard.detect → if HIGH → prepend hotline.
        If obfuscation regresses, this test fails."""
        out = self.engine._basic_feedback_with_crisis_guard('killmyself', -0.9)
        self.assertIn('988', out,
                      f'killmyself no-separator must include 988. Got: {out[:120]}')

    def test_obfuscated_dot_separator_triggers_hotline(self):
        """``k.i.l.l m.y.s.e.l.f`` should normalize-fuse to killmyself
        and trigger HIGH path."""
        out = self.engine._basic_feedback_with_crisis_guard(
            'I want to k.i.l.l m.y.s.e.l.f tonight', -0.9,
        )
        self.assertIn('988', out)

    def test_fullwidth_obfuscation_triggers_hotline(self):
        """Full-width IME chars ``ｋｉｌｌ ｍｙｓｅｌｆ`` NFKC-fold to ASCII
        in the obfuscation pass. Combined with English context so the
        locale guess routes to the en hotline — pure full-width input
        has no script-class signal and would default to zh-TW.
        """
        out = self.engine._basic_feedback_with_crisis_guard(
            'I cannot take this anymore, ｓｕｉｃｉｄｅ is the only way',
            -0.9,
        )
        self.assertIn('988', out)

    def test_fullwidth_obfuscation_no_locale_signal_defaults_zh_tw(self):
        """Pure full-width input with no script class hits the default
        fallback locale (zh-TW) — that is the deployed-in-Taiwan
        choice, documented and acceptable. Still triggers HIGH path so
        SOMETHING is shown."""
        out = self.engine._basic_feedback_with_crisis_guard('ｓｕｉｃｉｄｅ', -0.9)
        # Any one of the three hotlines is acceptable — what we MUST NOT
        # see is generic feedback with no hotline at all.
        any_hotline = any(s in out for s in ('1925', '988', '0120-279-338', '0570-783-556'))
        self.assertTrue(any_hotline, f'No hotline in: {out[:120]}')

    # ------------------------------------------------------------------
    # NON-HIGH — hotline must NOT appear (no false positives)
    # ------------------------------------------------------------------
    def test_medium_does_not_prepend_hotline(self):
        """MEDIUM ``撐不下去`` is hopelessness, not direct ideation.
        The hotline should NOT prepend (only the softer-tone preamble
        applies, and that's on the system prompt side, not the basic
        feedback output)."""
        out = self.engine._basic_feedback_with_crisis_guard('撐不下去', -0.6)
        self.assertNotIn('1925', out,
                         f'MEDIUM must NOT include 1925. Got: {out[:120]}')

    def test_positive_text_no_hotline(self):
        out = self.engine._basic_feedback_with_crisis_guard(
            '今天和朋友吃飯，超級開心！', 0.7,
        )
        self.assertNotIn('1925', out)
        self.assertNotIn('988', out)

    def test_neutral_text_no_hotline(self):
        out = self.engine._basic_feedback_with_crisis_guard('普通的一天', 0.0)
        self.assertNotIn('1925', out)
        self.assertNotIn('988', out)

    # ------------------------------------------------------------------
    # Cross-clause fusion FP guard (per second-pass review)
    # ------------------------------------------------------------------
    def test_benign_english_with_comma_no_space_no_hotline(self):
        """``end it,all meetings cancelled`` would normalize-fuse to
        ``enditallmeetings`` which contains ``enditall``. The
        phrasal-multi-word compacts were dropped to prevent this FP;
        the test pins that benign text still does NOT trigger HIGH."""
        out = self.engine._basic_feedback_with_crisis_guard(
            'end it,all meetings cancelled today', 0.0,
        )
        self.assertNotIn('988', out)
        self.assertNotIn('1925', out)


if __name__ == '__main__':
    unittest.main()
