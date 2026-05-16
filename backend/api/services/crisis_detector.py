"""Crisis-keyword detection for user-generated text.

Used by note save, community post create, and counselor/AI message paths
to surface a hotline banner when a user describes self-harm or suicidal
ideation. The detector is intentionally over-inclusive: false positives
just show a "you are not alone" banner with hotline numbers, which is
benign; false negatives leave a struggling user without support, which
is not. The detector NEVER auto-deletes or blocks content — staying
visible matters more than catching everything.

Regional hotlines surfaced (no API call — just static numbers):
  - Taiwan: 1925 (24/7) / 1995 (24/7)
  - Japan: よりそいホットライン 0120-279-338
  - US / international: 988 (suicide & crisis lifeline) / Befrienders.org

The keyword sets are deliberately short. Adding more entries here is
cheap but each addition is one more thing to maintain across three
languages, so prefer broad-stroke phrases over edge-case slang.
"""

import re

# Patterns are matched case-insensitively against the *full* text after
# stripping HTML and lowercasing. They're regex so we can capture
# variants like 我想死 / 想去死 / 死ぬしかない without listing each.
_CRISIS_PATTERNS = [
    # Mandarin (zh-TW / zh-CN)
    r'想[要]?死',
    r'不想活',
    r'想去死',
    r'結束(?:生命|這一切|自己)',
    r'自殺',
    r'活不下去',
    r'想要消失',
    r'割腕',
    r'自殘',
    r'吞藥',
    # English
    r'\bkill\s+myself\b',
    r'\bend\s+(?:it\s+all|my\s+life)\b',
    r"\bdon't\s+want\s+to\s+live\b",
    r'\bsuicide\b',
    r'\bsuicidal\b',
    r'\bself[-\s]?harm\b',
    r'\bcut\s+myself\b',
    # Japanese
    r'死にたい',
    r'消えたい',
    r'死ぬしかない',
    r'自殺',
    r'リストカット',
]

_compiled = [re.compile(p, re.IGNORECASE) for p in _CRISIS_PATTERNS]


def detect_crisis(text):
    """Return True if any crisis pattern matches the given text.

    Empty / None text returns False. We intentionally do NOT strip
    punctuation or normalise unicode — the patterns above are written
    to handle common shapes directly, and over-engineering here just
    means surprising false negatives.
    """
    if not text:
        return False
    return any(p.search(text) for p in _compiled)


# Hotline data is exposed for the API so the frontend can localise the
# numbers + descriptions itself. We keep it server-side too so backend
# logs and email follow-ups can reference the same canonical list.
HOTLINES = {
    'tw': [
        {'name': '1925 安心專線', 'number': '1925', 'description': '24/7 心理諮詢'},
        {'name': '生命線', 'number': '1995', 'description': '24/7 危機支援'},
        {'name': '張老師', 'number': '1980', 'description': '青少年諮詢'},
    ],
    'jp': [
        {'name': 'よりそいホットライン', 'number': '0120-279-338', 'description': '24時間対応'},
        {'name': 'いのちの電話', 'number': '0570-783-556', 'description': '10:00-22:00'},
    ],
    'us': [
        {'name': '988 Suicide & Crisis Lifeline', 'number': '988', 'description': '24/7 free & confidential'},
    ],
    'intl': [
        {'name': 'Befrienders Worldwide', 'number': 'https://befrienders.org', 'description': 'Find a helpline'},
    ],
}


def crisis_response_payload():
    """Standard payload to merge into an API response when a crisis
    keyword is detected. Frontend uses ``crisis_detected`` to decide
    whether to render the hotline banner overlay."""
    return {
        'crisis_detected': True,
        'hotlines': HOTLINES,
    }
