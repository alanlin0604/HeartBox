"""Lightweight content moderation for PublicPost create + report flow.

Two surfaces:

1. ``screen_content(text)`` — fast check before persisting a new post. Returns
   ``(allow: bool, reason: str|None)``. Catches obvious abuse keywords and
   spammy patterns. Per-user rate limits live on PublicPostThrottle (separate);
   this is purely about the text itself.

2. ``maybe_autohide_post(post)`` — called after a new PostReport is filed.
   Once a post hits ``AUTO_HIDE_THRESHOLD`` distinct reporters it gets
   ``is_active=False`` so it disappears from the feed pending admin review.

The keyword list is intentionally short and conservative; the goal is to
block the worst-case spam / slurs without over-policing legitimate
mental-health discussion (where words like "anxious", "lonely", or
"struggling" are normal and welcome).
"""

from __future__ import annotations

import re

# Distinct reporters needed to auto-hide. Tunable.
AUTO_HIDE_THRESHOLD = 3

# Hard-block patterns. Lowercase regex, word-boundary-aware where the term is
# context-free (slurs, ad spam). Mental-health vocabulary deliberately absent.
_BLOCK_PATTERNS = [
    # Ad spam — common patterns we've seen in similar apps
    re.compile(r'\b(?:viagra|cialis|crypto[-\s]?giveaway|free[-\s]?bitcoin)\b', re.I),
    re.compile(r'(?:t\.me/|wa\.me/|whatsapp[-\s]?\+\d+)', re.I),
    # Phone numbers / WeChat IDs that look like solicitation contact dumps
    re.compile(r'(加微信|加我微信|line\s*id|whatsapp).{0,3}[a-z0-9_]{4,}', re.I),
    # Generic invite spam ("赚钱" / "兼职" / "代购" with money emoji or URL)
    re.compile(r'(?:[赚兼代購购钱]).{0,20}(?:http|加群|加好友)', re.I),
]

# Soft signals — flag for review but don't block. Reserved for future use;
# returned as the second element of screen_content when present.
_FLAG_PATTERNS = [
    re.compile(r'\b(buy now|click here|限時優惠|限时优惠)\b', re.I),
]

MIN_LEN = 4  # below this we treat the post as content-less spam
MAX_LEN = 5000


def screen_content(text: str) -> tuple[bool, str | None]:
    """Return (allow, reason). reason is None when allowed."""
    if text is None:
        return False, 'empty'
    stripped = text.strip()
    if len(stripped) < MIN_LEN:
        return False, 'too_short'
    if len(stripped) > MAX_LEN:
        return False, 'too_long'
    for pat in _BLOCK_PATTERNS:
        if pat.search(stripped):
            return False, 'blocked_keyword'
    return True, None


def maybe_autohide_post(post) -> bool:
    """Hide the post if it has accumulated enough open reports. Returns True
    if the post was just deactivated by this call."""
    if not post.is_active:
        return False
    open_reports = post.reports.filter(status='open').values('reporter_id').distinct().count()
    if open_reports >= AUTO_HIDE_THRESHOLD:
        post.is_active = False
        post.save(update_fields=['is_active'])
        return True
    return False
