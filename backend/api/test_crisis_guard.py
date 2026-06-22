"""Unit tests for ``api.services.llm.crisis_guard.CrisisGuard``.

Pure unittest — no DB / no Django override needed. Run with:

    python manage.py test api.test_crisis_guard
    # or
    python -m unittest api.test_crisis_guard -v
"""
import unittest

from api.services.llm.crisis_guard import (
    CrisisGuard,
    CrisisMatch,
    HOTLINE_MESSAGE,
)


class TestDetectMandarinHigh(unittest.TestCase):
    """HIGH-severity zh-TW patterns from the legacy crisis_detector."""

    def test_direct_ideation(self):
        for txt in ['我想死', '想去死', '我不想活了', '結束生命', '結束自己', '我要自殺']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'HIGH')
            self.assertEqual(m.locale, 'zh-TW')

    def test_self_harm(self):
        for txt in ['想割腕', '自殘行為', '吞藥']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m)
            self.assertEqual(m.severity, 'HIGH')

    def test_should_review_queue_high(self):
        self.assertTrue(CrisisGuard.should_review_queue('我不想活了'))


class TestDetectMandarinMedium(unittest.TestCase):
    """MEDIUM severity — hopelessness, not direct ideation."""

    def test_hopelessness_phrases(self):
        for txt in ['撐不下去', '快撐不住', '活著好累', '真的累了', '厭世', '沒有希望', '沒有動力']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'MEDIUM', f'{txt!r} should be MEDIUM, got {m.severity}')

    def test_好累_fires_medium_intentionally(self):
        # 好累 IS a documented MEDIUM signal — the system intentionally
        # nudges a softer-tone preamble for everyday mild fatigue. Pinned
        # so a future "relax everything" refactor cannot silently drop it.
        for txt in ['今天上班好累', '昨天跑步好累', '工作好累但很充實']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match MEDIUM')
            self.assertEqual(m.severity, 'MEDIUM')

    def test_bare_tired_no_match(self):
        # Bare 累 / 累了 without any 好/真的/活著 prefix MUST NOT trigger —
        # this is the original false-positive risk the design called out
        # (every Taiwanese says "我累了" at the end of the day). The prior
        # ``if m is not None`` shape passed trivially even when the bug
        # returned; this is the stronger assertion that would actually
        # catch a regression.
        for txt in ['我累', '累', '累了']:
            self.assertIsNone(
                CrisisGuard.detect(txt),
                f'{txt!r} (bare fatigue) should NOT trigger crisis',
            )

    def test_想消失_now_matches(self):
        # Adversarial review caught: _CRISIS_PATTERNS required 要 ("想要消失")
        # but the obfuscation list allowed optional 要 ("想要?消失"), so
        # bare "我想消失" was silently missed. Both lists now use 想要?消失.
        m = CrisisGuard.detect('我想消失')
        self.assertIsNotNone(m, '想消失 should match HIGH')
        self.assertEqual(m.severity, 'HIGH')

    def test_medium_not_in_review_queue(self):
        self.assertFalse(CrisisGuard.should_review_queue('撐不下去'))


class TestHighWinsOverMedium(unittest.TestCase):
    """HIGH-first sweep: co-occurring HIGH + MEDIUM returns HIGH."""

    def test_high_beats_medium(self):
        m = CrisisGuard.detect('撐不下去了，我真的不想活')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')

    def test_high_in_middle_of_text(self):
        m = CrisisGuard.detect('最近工作很多，我想死，可是又捨不得家人')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')


class TestDetectEnglish(unittest.TestCase):
    def test_high_patterns(self):
        for txt in [
            'I want to kill myself',
            "I don't want to live anymore",
            'thinking of suicide',
            'suicidal ideation',
            'I cut myself',
        ]:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'HIGH')
            self.assertEqual(m.locale, 'en')

    def test_medium_patterns(self):
        for txt in ['I am so exhausted', "I can't go on anymore", 'feeling hopeless']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'MEDIUM')

    def test_case_insensitive(self):
        m = CrisisGuard.detect('KILL MYSELF')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')


class TestDetectJapanese(unittest.TestCase):
    def test_high_patterns(self):
        for txt in ['死にたい', '消えたい', '死ぬしかない', 'リストカット']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'HIGH')
            self.assertEqual(m.locale, 'ja')

    def test_medium_patterns(self):
        for txt in ['もう疲れた', 'もう無理', 'もう限界', 'しんどい', '絶望', '希望がない']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'MEDIUM')


class TestDetectNegative(unittest.TestCase):
    """Things that must NOT trigger anything."""

    def test_empty_inputs(self):
        for txt in ['', None]:
            self.assertIsNone(CrisisGuard.detect(txt or ''))

    def test_whitespace(self):
        self.assertIsNone(CrisisGuard.detect('   \n\n  '))

    def test_positive_journal(self):
        for txt in [
            '今天和朋友吃飯，很開心',
            '工作完成了，有成就感',
            'I had a great day at the park',
            '友達と楽しい時間を過ごした',
        ]:
            self.assertIsNone(CrisisGuard.detect(txt), f'{txt!r} should not match')


class TestLocaleGuess(unittest.TestCase):
    def test_japanese_via_hiragana(self):
        m = CrisisGuard.detect('死にたい')
        self.assertEqual(m.locale, 'ja')

    def test_zh_via_cjk(self):
        m = CrisisGuard.detect('我不想活')
        self.assertEqual(m.locale, 'zh-TW')

    def test_en_via_ascii(self):
        m = CrisisGuard.detect('I want to kill myself')
        self.assertEqual(m.locale, 'en')

    def test_explicit_locale_overrides(self):
        m = CrisisGuard.detect('I want to kill myself', locale='zh-TW')
        self.assertEqual(m.locale, 'zh-TW')


class TestInjectPreamble(unittest.TestCase):
    def test_zh_preamble(self):
        out = CrisisGuard.inject_preamble('你是助理。', locale='zh-TW')
        self.assertIn('最高優先', out)
        self.assertIn('1925', out)
        self.assertTrue(out.endswith('你是助理。'))

    def test_en_preamble(self):
        out = CrisisGuard.inject_preamble('You are an assistant.', locale='en')
        self.assertIn('HIGHEST PRIORITY', out)
        self.assertIn('988', out)

    def test_ja_preamble(self):
        out = CrisisGuard.inject_preamble('あなたはアシスタントです。', locale='ja')
        self.assertIn('最優先', out)
        self.assertIn('0120-279-338', out)


class TestPrependHotline(unittest.TestCase):
    def test_zh_hotline_prepended(self):
        out = CrisisGuard.prepend_hotline('我聽到你的感受了。', locale='zh-TW')
        self.assertIn('1925', out)
        self.assertIn('我聽到你的感受了。', out)

    def test_en_hotline_prepended(self):
        out = CrisisGuard.prepend_hotline('I hear you.', locale='en')
        self.assertIn('988', out)
        self.assertIn('I hear you.', out)

    def test_ja_hotline_prepended(self):
        out = CrisisGuard.prepend_hotline('話してくれてありがとう。', locale='ja')
        self.assertIn('0120-279-338', out)
        self.assertIn('話してくれてありがとう。', out)

    def test_hotline_strips_leading_whitespace(self):
        out = CrisisGuard.prepend_hotline('\n\n   actual response', locale='en')
        # Hotline message ends with \n\n; user text should not have leading whitespace.
        self.assertIn('actual response', out)
        # No triple-blank line between hotline and content.
        self.assertNotIn('\n\n\n   actual', out)


class TestHotlineMessageShape(unittest.TestCase):
    def test_all_locales_present(self):
        for loc in ['zh-TW', 'en', 'ja']:
            self.assertIn(loc, HOTLINE_MESSAGE)
            self.assertTrue(HOTLINE_MESSAGE[loc], f'{loc} hotline message is empty')


class TestWantToDieAndOverdose(unittest.TestCase):
    """Coverage for the bug-#14 gap: ``want to die`` family + overdose / jump off."""

    def test_want_to_die_variants(self):
        for txt in [
            'I want to die',
            'i want to die tonight',
            'sometimes I just want to die',
            'wanting to die for years',
            'I wanted to die last night',
            'she wants to die',
        ]:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'HIGH', f'{txt!r} should be HIGH')

    def test_overdose_pattern(self):
        for txt in ['considering overdose tonight', 'planning an overdose']:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match')
            self.assertEqual(m.severity, 'HIGH')

    def test_jump_off_pattern(self):
        m = CrisisGuard.detect('I might jump off the bridge')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')


class TestObfuscationBypass(unittest.TestCase):
    """Coverage for bug #13: separator-character obfuscation must still trip."""

    def test_dot_separator_english(self):
        m = CrisisGuard.detect('I want to k.i.l.l m.y.s.e.l.f tonight')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')

    def test_space_separator_english(self):
        m = CrisisGuard.detect('I want to k i l l m y s e l f tonight')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')

    def test_punctuation_separator_chinese(self):
        m = CrisisGuard.detect('我.想.死了')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')

    def test_underscored_obfuscation(self):
        m = CrisisGuard.detect('s_u_i_c_i_d_e plan')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')

    def test_mixed_obfuscation_overdose(self):
        m = CrisisGuard.detect('thinking about an o-v-e-r-d-o-s-e')
        self.assertIsNotNone(m)
        self.assertEqual(m.severity, 'HIGH')

    def test_clean_text_unaffected(self):
        # Normal text without obfuscation should still be classified normally.
        self.assertIsNone(CrisisGuard.detect('今天和朋友吃飯，很開心'))

    def test_no_separator_smashed_input(self):
        # Adversarial review caught: the previous obfuscation pass skipped
        # the scan when ``normalized == text.lower()``, so ALREADY-smashed
        # inputs slipped through. These (single-token compacts only) must
        # trigger HIGH. Phrasal multi-word compacts (enditall / endmylife /
        # dontwanttolive / jumpoff) were dropped in a later round to stop
        # cross-clause FPs — see test_phrasal_compacts_removed_no_obfuscation_match.
        for txt in [
            'killmyself',
            'iwanttodie',
            'wantingtodie',
            'wanttokill',
            'cutmyself',
            'selfharm',
            'suicide',
        ]:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} should match HIGH (no-separator case)')
            self.assertEqual(m.severity, 'HIGH', f'{txt!r} should be HIGH')

    def test_cross_sentence_does_not_fuse(self):
        # Adversarial review caught: whole-string normalize fused
        # "end it. All meetings" -> "enditall" and false-routed benign
        # English to the moderation review queue. Per-clause split MUST
        # leave these untouched (no HIGH match). A second-pass review
        # then found three further fusion-FP routes: comma-no-space,
        # U+2026 ellipsis, and the dropped multi-word compacts.
        #
        # NOTE: cases like "Stop the press. End it all came together" are
        # NOT in this list — the raw pattern ``\bend\s+it\s+all\b`` matches
        # them legitimately and that's a coverage-vs-precision trade-off
        # of the keyword approach, not a normalize-fusion bug.
        for txt in [
            'The boss said end it. All meetings cancelled.',
            'Jump. Off the deck looks dangerous.',
            'self, harm reduction is a public-health approach',
            'will kill, my self image is fine',
            'Let me end it: all the bickering must stop.',
            # Second-pass review additions:
            'end it,all meetings',                       # comma + no space
            'end it…all I want is peace',                # U+2026 ellipsis
            'end it...all I want is peace',              # ASCII ellipsis
            'I should jump,off the deck',                # comma + no space
            'don’t want to live in this city',       # smart-quote + benign
            'kill, my self-image is fine',               # comma fuses kill+myself
        ]:
            m = CrisisGuard.detect(txt)
            self.assertTrue(
                m is None or m.severity != 'HIGH',
                f'{txt!r} should NOT trigger HIGH — got {m}',
            )

    def test_phrasal_compacts_removed_no_obfuscation_match(self):
        # The phrasal multi-word English compacts (enditall, endmylife,
        # dontwanttolive, jumpoff) were dropped after adversarial review
        # because their fused form composed innocently in benign English.
        # Smashed forms of these phrases now intentionally rely on the
        # raw pattern (which requires whitespace between words). Verify
        # the no-space variants are silently skipped — the trade-off the
        # design accepts.
        for txt in ['enditall', 'endmylife', 'dontwanttolive', 'jumpoff']:
            m = CrisisGuard.detect(txt)
            # These MUST not raise HIGH on the obfuscation pass alone —
            # we documented this as the acceptable coverage loss.
            self.assertTrue(
                m is None or m.severity != 'HIGH',
                f'{txt!r} no-space phrasal compact should not match HIGH',
            )

    def test_fullwidth_obfuscation(self):
        # Adversarial review caught: full-width IME chars (ｋｉｌｌ ｍｙｓｅｌｆ)
        # passed straight through. NFKC normalization in the obfuscation
        # path must fold these back to ASCII before pattern matching.
        for txt in [
            'ｋｉｌｌ ｍｙｓｅｌｆ',
            'ｓｕｉｃｉｄｅ tonight',
            'ｗａｎｔ ｔｏ ｄｉｅ',
        ]:
            m = CrisisGuard.detect(txt)
            self.assertIsNotNone(m, f'{txt!r} (full-width) should match HIGH')
            self.assertEqual(m.severity, 'HIGH')


class TestLocaleGuessDominantScript(unittest.TestCase):
    """Coverage for bug #12: dominant-script wins, not first-hit."""

    def test_english_dominant_over_single_cjk_char(self):
        # Sentence is overwhelmingly English; a single CJK char should not
        # flip the hotline to Taiwan.
        m = CrisisGuard.detect('I really want to kill myself, mom 媽')
        self.assertIsNotNone(m)
        self.assertEqual(m.locale, 'en')

    def test_japanese_dominant_over_english_word(self):
        m = CrisisGuard.detect('死にたい、もう限界 kill')
        self.assertIsNotNone(m)
        self.assertEqual(m.locale, 'ja')

    def test_chinese_dominant_unchanged(self):
        m = CrisisGuard.detect('我真的不想活了')
        self.assertIsNotNone(m)
        self.assertEqual(m.locale, 'zh-TW')

    def test_pure_english_unchanged(self):
        m = CrisisGuard.detect('I want to die')
        self.assertEqual(m.locale, 'en')

    def test_no_text_falls_back_to_zh_tw(self):
        # Numeric-only / no script chars defaults to zh-TW (capstone audience).
        from api.services.llm.crisis_guard import CrisisGuard as G
        self.assertEqual(G._guess_locale('1234567890'), 'zh-TW')


class TestNoDuplicateCrisisPatterns(unittest.TestCase):
    """Bug #20 (MEDIUM): 自殺 was listed twice. Keep dedup invariant."""

    def test_no_duplicate_patterns(self):
        from api.services.crisis_detector import _CRISIS_PATTERNS
        self.assertEqual(
            len(_CRISIS_PATTERNS),
            len(set(_CRISIS_PATTERNS)),
            'crisis_detector._CRISIS_PATTERNS contains duplicates',
        )


if __name__ == '__main__':
    unittest.main()
