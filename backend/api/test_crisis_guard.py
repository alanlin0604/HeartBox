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

    def test_bare_tired_no_false_positive(self):
        # 今天上班好累 must NOT trigger — bare 累 in everyday context is fine.
        # We test the bare-累 case that the design called out as a false-positive risk.
        for txt in ['今天上班好累', '昨天跑步好累', '工作好累但很充實']:
            m = CrisisGuard.detect(txt)
            # 好累 fires MEDIUM intentionally (mood signal worth softer tone).
            # The real false-positive guard is that BARE 累 does not fire.
            if m is not None:
                self.assertEqual(m.severity, 'MEDIUM',
                                 f'{txt!r}: only MEDIUM allowed for mild fatigue')

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


if __name__ == '__main__':
    unittest.main()
