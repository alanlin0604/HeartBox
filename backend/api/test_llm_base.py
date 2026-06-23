"""Unit tests for ``api.services.llm.base.LLMProvider.parse_json_tolerant``
and the underlying ``_balanced_json_objects`` generator.

Pure-Python — no Django setup, no DB. Run with:

    python manage.py test api.test_llm_base
    # or
    python -m unittest api.test_llm_base -v

These tests pin behaviors the Phase 0b adversarial review specifically
called out:
  * brace-walker must respect string literals (so a ``{`` inside ``"..."``
    does not get counted as opening another object)
  * backslash-escaped quotes inside strings must NOT toggle string state
  * if the first balanced substring fails ``json.loads``, the walker
    must slide past it and try the next candidate
  * a top-level array must NOT silently return (callers expect a dict)
  * scan is capped at 5 candidates to avoid pathological adversarial input
  * ``_first_balanced_json_object`` back-compat shim still returns only
    the first candidate
"""
import unittest

from api.services.llm.base import LLMProvider, LLMProviderError


class TestParseJsonTolerant(unittest.TestCase):

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------
    def test_plain_json_object(self):
        out = LLMProvider.parse_json_tolerant('{"a": 1, "b": "x"}')
        self.assertEqual(out, {'a': 1, 'b': 'x'})

    def test_json_with_whitespace_around(self):
        out = LLMProvider.parse_json_tolerant('   \n  {"a": 1}\n\n  ')
        self.assertEqual(out, {'a': 1})

    def test_nested_objects(self):
        raw = '{"a": {"b": {"c": 1}}}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'a': {'b': {'c': 1}}})

    def test_unicode_content(self):
        out = LLMProvider.parse_json_tolerant('{"reply": "今天好累，要多休息"}')
        self.assertEqual(out['reply'], '今天好累，要多休息')

    # ------------------------------------------------------------------
    # Markdown fence stripping
    # ------------------------------------------------------------------
    def test_markdown_fence_json_label(self):
        raw = '```json\n{"sentiment_score": -0.5, "stress_index": 7}\n```'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out['sentiment_score'], -0.5)
        self.assertEqual(out['stress_index'], 7)

    def test_markdown_fence_bare(self):
        raw = '```\n{"a": 1}\n```'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'a': 1})

    # ------------------------------------------------------------------
    # Prose + JSON (the small-model preamble case)
    # ------------------------------------------------------------------
    def test_prose_then_json(self):
        raw = 'Sure! Here is the JSON you asked for: {"sentiment_score": 0.3}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out['sentiment_score'], 0.3)

    def test_json_then_trailing_prose(self):
        raw = '{"a": 1}\n\nLet me know if you need clarification.'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'a': 1})

    # ------------------------------------------------------------------
    # Multi-candidate slide (the core review fix)
    # ------------------------------------------------------------------
    def test_prose_brace_then_real_json(self):
        """A literal ``{`` appearing inside a quoted phrase before the
        real JSON object. The brace walker latches on the first one
        which fails parse, then must slide to the second."""
        raw = 'Here is the JSON: "with {prose} in it" {"actual": 1}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'actual': 1})

    def test_multiple_objects_returns_first_dict(self):
        raw = '{"first": 1}\n{"second": 2}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'first': 1})

    def test_array_then_object_returns_object(self):
        """First balanced ``{ ... }`` is the object inside the array; the
        walker yields that, but it is not a top-level dict per the
        parser's contract — caller wants the standalone object."""
        raw = '[1, 2, 3] {"actual": 5}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'actual': 5})

    # ------------------------------------------------------------------
    # String-state machine (escape + quote handling)
    # ------------------------------------------------------------------
    def test_string_with_escaped_quote(self):
        """``{"k": "a\\"b"}`` — escaped quote must not end the string,
        so the closing ``}`` is correctly identified."""
        raw = '{"k": "a\\"b"}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'k': 'a"b'})

    def test_string_with_brace_inside(self):
        """``{"k": "value with } and { inside"}`` — braces inside a
        string literal must NOT affect brace depth."""
        raw = '{"k": "value with } and { inside"}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out['k'], 'value with } and { inside')

    def test_string_with_double_backslash(self):
        """``"a\\\\"`` is a JSON string containing one literal backslash;
        the closing ``"`` must still end the string."""
        raw = '{"k": "a\\\\"}'
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out['k'], 'a\\')

    # ------------------------------------------------------------------
    # Failure modes
    # ------------------------------------------------------------------
    def test_empty_input_raises(self):
        with self.assertRaises(LLMProviderError) as ctx:
            LLMProvider.parse_json_tolerant('')
        self.assertIn('empty', str(ctx.exception).lower())

    def test_no_json_in_response_raises(self):
        with self.assertRaises(LLMProviderError) as ctx:
            LLMProvider.parse_json_tolerant('I cannot help with this request.')
        msg = str(ctx.exception)
        self.assertIn('no JSON object', msg)

    def test_top_level_array_raises(self):
        """A bare list is not what callers asked for — they want a dict.
        The parser must NOT silently return the list."""
        with self.assertRaises(LLMProviderError):
            LLMProvider.parse_json_tolerant('[1, 2, 3]')

    def test_top_level_string_raises(self):
        with self.assertRaises(LLMProviderError):
            LLMProvider.parse_json_tolerant('"just a string"')

    def test_unterminated_brace_raises(self):
        """No matching ``}`` in the input — the walker should yield nothing."""
        with self.assertRaises(LLMProviderError):
            LLMProvider.parse_json_tolerant('{unterminated and no close')

    def test_malformed_json_with_one_candidate_raises(self):
        """First balanced substring parses-fails AND there are no more
        candidates → raise with the underlying parse error."""
        with self.assertRaises(LLMProviderError) as ctx:
            LLMProvider.parse_json_tolerant('{ this is not valid json }')
        # message should hint at the parse error
        self.assertTrue(
            'parse' in str(ctx.exception).lower()
            or 'no JSON' in str(ctx.exception),
            f'unexpected message: {ctx.exception}'
        )

    # ------------------------------------------------------------------
    # Cap on adversarial input
    # ------------------------------------------------------------------
    def test_max_candidates_cap(self):
        """The walker stops after 5 candidates. If the real JSON is the
        7th balanced block, the parser will not reach it. Caller is
        expected to truncate adversarially long inputs upstream.

        This test pins the cap so a future change to ``max_candidates``
        is intentional, not accidental."""
        bogus = '{bad} ' * 6              # six unparseable candidates
        real = '{"actual": 1}'             # the legitimate object
        raw = bogus + real
        with self.assertRaises(LLMProviderError):
            LLMProvider.parse_json_tolerant(raw)

    def test_five_candidates_within_cap_succeeds(self):
        """Exactly at the cap boundary: 4 bogus + 1 good = 5 attempts,
        last one parses."""
        bogus = '{bad} ' * 4
        real = '{"actual": 1}'
        raw = bogus + real
        out = LLMProvider.parse_json_tolerant(raw)
        self.assertEqual(out, {'actual': 1})


class TestBalancedJsonObjectsGenerator(unittest.TestCase):
    """Direct tests of the underlying ``_balanced_json_objects`` generator.
    Tests at this layer pin invariants the parser builds on."""

    def _collect(self, text, **kw):
        return list(LLMProvider._balanced_json_objects(text, **kw))

    def test_no_brace_yields_nothing(self):
        self.assertEqual(self._collect('hello world'), [])

    def test_single_balanced_object(self):
        self.assertEqual(self._collect('foo {"a":1} bar'), ['{"a":1}'])

    def test_multiple_balanced_objects(self):
        out = self._collect('{"a":1} {"b":2} {"c":3}')
        self.assertEqual(out, ['{"a":1}', '{"b":2}', '{"c":3}'])

    def test_unclosed_brace_after_yielded_object(self):
        """First object parses fine, second has no close → only first
        yielded, then generator stops."""
        out = self._collect('{"a":1} {unclosed')
        self.assertEqual(out, ['{"a":1}'])

    def test_string_quoted_brace_not_counted(self):
        """Braces inside a string literal must not affect depth."""
        out = self._collect('{"k": "}{["}')
        self.assertEqual(out, ['{"k": "}{["}'])

    def test_max_candidates_param(self):
        text = '{"a":1} {"b":2} {"c":3} {"d":4}'
        self.assertEqual(len(self._collect(text, max_candidates=2)), 2)
        self.assertEqual(len(self._collect(text, max_candidates=10)), 4)


class TestFirstBalancedJsonObjectBackCompat(unittest.TestCase):
    """The shim ``_first_balanced_json_object`` must still exist and
    return the first balanced substring (or None) — Phase 0b code may
    still call it; renaming would be a breaking change."""

    def test_returns_first_object(self):
        out = LLMProvider._first_balanced_json_object('foo {"a":1} {"b":2}')
        self.assertEqual(out, '{"a":1}')

    def test_returns_none_when_no_brace(self):
        self.assertIsNone(LLMProvider._first_balanced_json_object('no braces'))

    def test_returns_none_when_unterminated(self):
        self.assertIsNone(LLMProvider._first_balanced_json_object('{open with no close'))


if __name__ == '__main__':
    unittest.main()
