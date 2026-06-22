"""Independent crisis-keyword regex layer.

Runs BEFORE every LLM call. The LLM itself is not the safety net — this is.
Defense-in-depth: even if the model misbehaves or the provider is mocked,
the safety preamble + hotline string is concatenated by application code.

Two severity tiers:

  HIGH    — direct self-harm / suicidal ideation. Triggers:
            - Safety preamble prepended to the system prompt.
            - Hotline string prepended to the final response.
            - ``should_review_queue()`` returns True so callers may file a
              moderation/review record.
  MEDIUM  — hopelessness phrases (累了, 撐不下去, exhausted, 疲れた).
            Triggers preamble only; no review queue.

HIGH-first sweep: ``detect()`` returns the highest severity match across all
patterns. ``撐不下去了我不想活`` returns HIGH (from 不想活), not MEDIUM.

We re-use ``api.services.crisis_detector._CRISIS_PATTERNS`` for the HIGH layer
so the two stay in lockstep — single source of truth for direct-ideation
detection.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from api.services.crisis_detector import _CRISIS_PATTERNS as _HIGH_PATTERNS_RAW

Severity = Literal['HIGH', 'MEDIUM']
Locale = Literal['zh-TW', 'en', 'ja']

# Hopelessness / exhaustion phrases. MEDIUM-only — these alone don't warrant
# a review queue entry, but they do warrant a softer-tone preamble.
#
# 累了 false-positive guard: bare "累" is too common ("今天上班好累") to fire
# alone. We require either:
#   - sentence-end isolation: "累了" or "累了。" at end of a short utterance, OR
#   - co-occurrence with a hopelessness signal in the same text.
# Implemented by NOT including bare 累了 in MEDIUM patterns directly; only the
# in-context variants (活著很累, 真的累了想..., 太累了不想...) trigger MEDIUM.
_MEDIUM_PATTERNS_RAW: list[str] = [
    # Mandarin
    r'撐不下去',
    r'快撐不住',
    r'活著(?:好|很|真的)?累',
    r'(?:真的|實在|好)累(?:了|到)',
    r'厭世',
    r'(?:無望|沒(?:有)?希望)',
    r'(?:沒(?:有)?|找不到)動力',
    r'好(?:累|疲憊|疲倦|想哭)',
    # English
    r'\b(?:so|really|too)\s+exhausted\b',
    r'\bhopeless\b',
    r"\bcan't\s+(?:go\s+on|do\s+this\s+anymore)\b",
    r'\bgiving\s+up\b',
    r"\bnothing\s+matters\b",
    # Japanese
    r'もう(?:疲れた|無理|限界)',
    r'(?:しんどい|つらい)+(?:です|よ|な)?',
    r'(?:絶望|希望がない)',
]

_HIGH_COMPILED = [re.compile(p, re.IGNORECASE) for p in _HIGH_PATTERNS_RAW]
_MEDIUM_COMPILED = [re.compile(p, re.IGNORECASE) for p in _MEDIUM_PATTERNS_RAW]

# Obfuscation defense — three pieces that together close the gaps the
# adversarial review surfaced:
#
# 1. ``_NORMALIZE`` strips every \W_ char (punctuation, whitespace,
#    underscore) within a clause. CJK chars are \w in Python's default
#    Unicode regex, so 想死 / 死にたい pass through unchanged.
#
# 2. ``_CLAUSE_SPLIT`` splits text on sentence-ending punctuation (. ! ? \n)
#    or clause-ending separators (, followed by whitespace, ; :) BEFORE
#    normalize runs. Without this, "end it. All meetings cancelled" would
#    fuse to "enditall" and falsely route benign English to the moderation
#    review queue. Per-clause normalization preserves the legitimate
#    bypass case (``k.i.l.l m.y.s.e.l.f`` lives entirely inside one
#    clause and still fuses to ``killmyself``).
#
# 3. ``unicodedata.normalize('NFKC', text)`` folds full-width ASCII
#    (ｋｉｌｌ U+FF21-FF5A, common on Japanese/Chinese IMEs) back to plain
#    ASCII before pattern matching. Cyrillic/Greek homoglyphs and
#    leetspeak are NOT covered (would need a confusables table); a TODO
#    is left in code for v2.
_NORMALIZE = re.compile(r'[\W_]+')
# Sentence/clause boundaries. Crucially the ``.!?`` punctuation only splits
# when followed by whitespace or end-of-string — otherwise ``k.i.l.l`` and
# ``我.想.死`` would be shredded into single-letter clauses and the
# obfuscation defense the split was meant to serve would be defeated.
# CJK full-width 。！？ + line breaks always split. Commas only split if
# followed by whitespace (English convention) — bare commas inside a
# tokenized identifier do not.
_CLAUSE_SPLIT = re.compile(r'[.!?](?=\s|$)|[。！？\n]+|,(?=\s)|[;:]')

# Compact HIGH-severity patterns: no \b, no \s+ — designed to match
# *normalized* text where all separators have been stripped.
_HIGH_OBFUSCATION_PATTERNS: list[str] = [
    # English
    r'killmyself',
    r'want(?:ing|s|ed)?todie',
    r'wanttokill',
    r'endmylife',
    r'enditall',
    r'dontwanttolive',
    r'cutmyself',
    r'selfharm',
    r'suicide',
    r'suicidal',
    r'overdose',
    r'jumpoff',
    # zh-TW / zh-CN — CJK passes \W normalize unchanged
    r'想[要]?死',
    r'不想活',
    r'想去死',
    r'結束(?:生命|這一切|自己)',
    r'自殺',
    r'活不下去',
    r'想要?消失',
    r'割腕',
    r'自殘',
    r'吞藥',
    # Japanese
    r'死にたい',
    r'消えたい',
    r'死ぬしかない',
    r'リストカット',
]
_HIGH_OBFUSCATION_COMPILED = [
    re.compile(p, re.IGNORECASE) for p in _HIGH_OBFUSCATION_PATTERNS
]


def _obfuscation_hits(text: str) -> list[str]:
    """Per-clause normalized scan against the compact HIGH list.

    NFKC folds full-width input first so ``ｋｉｌｌ ｍｙｓｅｌｆ`` is folded to
    ``kill myself`` before normalization. Returns the list of matched
    pattern strings (empty = no obfuscation hit).
    """
    folded = unicodedata.normalize('NFKC', text).lower()
    hits: list[str] = []
    for clause in _CLAUSE_SPLIT.split(folded):
        normalized = _NORMALIZE.sub('', clause)
        if not normalized:
            continue
        for p in _HIGH_OBFUSCATION_COMPILED:
            if p.search(normalized):
                hits.append(p.pattern)
    return hits

# CJK script ranges for cheap locale guessing. ``findall`` lets us *count*
# script characters so the dominant script wins rather than the first script
# encountered — the prior ``search``-first behavior mis-routed "I really
# want to kill myself, 媽" to zh-TW because of a single CJK char.
_HIRAGANA_KATAKANA = re.compile(r'[぀-ヿ]')
_CJK = re.compile(r'[一-鿿]')
_ASCII_ALPHA = re.compile(r'[A-Za-z]')

# Hotline preamble per locale. Prepended verbatim by callers when HIGH.
HOTLINE_MESSAGE: dict[Locale, str] = {
    'zh-TW': (
        '💜 看到你寫下的內容，我很關心你的狀態。請記得你並不孤單，'
        '台灣安心專線 1925（24小時免費）或生命線 1995 都隨時在線陪伴你。\n\n'
    ),
    'en': (
        '💜 I noticed what you wrote and I am concerned for you. '
        'You are not alone — please call 988 Suicide & Crisis Lifeline '
        '(US, 24/7 free & confidential) or visit befrienders.org to find help nearby.\n\n'
    ),
    'ja': (
        '💜 あなたの書き込みを読みました。一人で抱え込まないでください。'
        'よりそいホットライン（0120-279-338, 24時間対応）または'
        'いのちの電話（0570-783-556）に連絡できます。\n\n'
    ),
}

# Safety preamble injected into the system prompt when HIGH detected.
# Steers the model itself toward the right tone before it generates a token.
_SAFETY_PREAMBLE: dict[Locale, str] = {
    'zh-TW': (
        '【最高優先】使用者表達了可能涉及自傷或自殺意念的內容。請：\n'
        '1. 用溫和、不評判的語氣回應，先肯定他們願意說出來的勇氣\n'
        '2. 不要說教，不要直接否定他們的感受\n'
        '3. 鼓勵立即聯繫台灣安心專線 1925 或就近就醫\n'
        '4. 強調他們並不孤單，有人願意傾聽\n'
        '5. 不要承諾保密，不要做專業診斷\n\n'
    ),
    'en': (
        '[HIGHEST PRIORITY] The user may be expressing self-harm or suicidal ideation. Please:\n'
        '1. Respond with warmth, no judgment; acknowledge the courage it took to share\n'
        '2. Do not lecture or dismiss their feelings\n'
        '3. Encourage them to call 988 immediately or visit an ER\n'
        '4. Emphasize they are not alone and someone is willing to listen\n'
        '5. Do not promise confidentiality; do not give a clinical diagnosis\n\n'
    ),
    'ja': (
        '【最優先】ユーザーが自傷や自殺の考えを表現している可能性があります。以下を守ってください：\n'
        '1. 温かく、判断せずに対応し、話してくれた勇気をまず受けとめる\n'
        '2. 説教や感情の否定をしない\n'
        '3. よりそいホットライン 0120-279-338 への連絡を勧める\n'
        '4. 一人ではないこと、聴く人がいることを伝える\n'
        '5. 守秘を約束しない、診断もしない\n\n'
    ),
}


@dataclass(frozen=True)
class CrisisMatch:
    """A single crisis-keyword hit. ``matched_keywords`` is the set of raw
    regex patterns that matched (useful for logs)."""
    severity: Severity
    matched_keywords: tuple[str, ...] = field(default_factory=tuple)
    locale: Locale = 'zh-TW'


class CrisisGuard:
    """Deterministic, defense-in-depth crisis layer.

    Use as a class — no instances needed. All methods are class/static.

        match = CrisisGuard.detect(text)
        if match is not None:
            system = CrisisGuard.inject_preamble(system, match.locale)
        answer = llm.chat(system=system, user=text)
        if match and match.severity == 'HIGH':
            answer = CrisisGuard.prepend_hotline(answer, match.locale)
    """

    @classmethod
    def detect(cls, text: str, *, locale: Locale | None = None) -> CrisisMatch | None:
        """Return the highest-severity match for ``text``, or None.

        HIGH-first sweep: as soon as any HIGH pattern hits, return HIGH (so
        co-occurring MEDIUM signals don't downgrade severity).
        """
        if not text:
            return None

        loc: Locale = locale or cls._guess_locale(text)

        # HIGH first — raw scan.
        high_hits = [p.pattern for p in _HIGH_COMPILED if p.search(text)]

        # Obfuscation defense: per-clause normalized scan. Runs unconditionally
        # when raw missed — including the no-separator case ``killmyself`` that
        # an earlier version of this guard skipped because the normalized text
        # equalled the input. Per-clause split prevents cross-sentence fusion
        # (``end it. All meetings`` no longer collapses to ``enditall``).
        if not high_hits:
            obf_hits = _obfuscation_hits(text)
            if obf_hits:
                high_hits = obf_hits

        if high_hits:
            return CrisisMatch(
                severity='HIGH',
                matched_keywords=tuple(high_hits),
                locale=loc,
            )

        med_hits = [p.pattern for p in _MEDIUM_COMPILED if p.search(text)]
        if med_hits:
            return CrisisMatch(
                severity='MEDIUM',
                matched_keywords=tuple(med_hits),
                locale=loc,
            )

        return None

    @classmethod
    def should_review_queue(cls, text: str) -> bool:
        """True if a moderation review should be created. HIGH only."""
        m = cls.detect(text)
        return m is not None and m.severity == 'HIGH'

    @classmethod
    def inject_preamble(cls, system_prompt: str, locale: Locale = 'zh-TW') -> str:
        """Prepend the safety preamble to a system prompt. Idempotent? No —
        caller decides whether to call it; double-injecting would be silly."""
        preamble = _SAFETY_PREAMBLE.get(locale, _SAFETY_PREAMBLE['zh-TW'])
        return preamble + system_prompt

    @classmethod
    def prepend_hotline(cls, response_text: str, locale: Locale = 'zh-TW') -> str:
        """Prepend the localized hotline message to a model response.

        This is the belt-and-braces layer: even if the LLM ignores the
        preamble, our application code guarantees the hotline appears.
        """
        hotline = HOTLINE_MESSAGE.get(locale, HOTLINE_MESSAGE['zh-TW'])
        return hotline + (response_text or '').lstrip()

    # ------------------------------------------------------------------
    # Internal: cheap locale guess from CJK / hiragana / latin presence.
    # ------------------------------------------------------------------
    @staticmethod
    def _guess_locale(text: str) -> Locale:
        # Count chars per script so the *dominant* script picks the hotline.
        # Search-first behavior misrouted code-switching text: one CJK char in
        # an otherwise-English sentence was routing US-style crisis content to
        # the Taiwan hotline.
        h = len(_HIRAGANA_KATAKANA.findall(text))
        c = len(_CJK.findall(text))
        a = len(_ASCII_ALPHA.findall(text))
        if h > max(c, a):
            return 'ja'
        if a > max(h, c):
            return 'en'
        if c > 0:
            return 'zh-TW'
        return 'zh-TW'
