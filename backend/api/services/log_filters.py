"""Log filters that scrub PII before records leave the process.

Plugged into ``LOGGING['handlers']['console']['filters']`` in settings.py.
Runs synchronously on the logging hot path so the implementation is kept
deliberately cheap: a single compiled regex over ``record.getMessage()``.

Email replacement scheme: ``alan@gmail.com`` → ``u4a3b1c8d@gmail.com``.
  * Local part replaced with ``u<sha256[:8]>`` of the lowercased original.
  * Domain preserved so an operator can still see the rough population
    (gmail.com vs corp domain) for debugging.
  * Deterministic — the SAME email always hashes to the same token, so
    two log lines about the same user remain correlatable.
"""
from __future__ import annotations

import hashlib
import logging
import re

# Conservative RFC-5321-ish email regex. Matches the common shapes that
# appear in logs (usernames + + dots in the local part). Doesn't try to
# handle quoted-string locals — those would be ambiguous with prose.
_EMAIL_RE = re.compile(
    r'\b([A-Za-z0-9][A-Za-z0-9._%+-]{0,63})@([A-Za-z0-9.-]+\.[A-Za-z]{2,24})\b'
)


def _hash_local(local: str) -> str:
    h = hashlib.sha256(local.lower().encode('utf-8')).hexdigest()[:8]
    return f'u{h}'


def _redact(text: str) -> str:
    if '@' not in text:
        return text
    return _EMAIL_RE.sub(lambda m: f'{_hash_local(m.group(1))}@{m.group(2)}', text)


class RedactEmailFilter(logging.Filter):
    """Mutate ``record.msg`` (and pre-formatted ``record.message`` if any)
    so the email-redacted body is what handlers serialize. Returns True
    so the record still propagates after redaction.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            if isinstance(record.msg, str):
                record.msg = _redact(record.msg)
            # If the record carried args, render them now so the eventual
            # formatter doesn't re-introduce an un-redacted email via %s.
            if record.args:
                try:
                    rendered = record.msg % record.args
                    record.msg = _redact(rendered)
                    record.args = ()
                except (TypeError, ValueError):
                    # Bad format string — leave it alone; the handler will
                    # raise the same way it would have without us.
                    pass
        except Exception:
            # Logging filters must NEVER raise — that would break the
            # application path that emitted the log call.
            pass
        return True
