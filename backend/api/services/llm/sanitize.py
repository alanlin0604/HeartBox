"""LLM-output scrubber: defense-in-depth strip of prompt-template leakage.

The root cause of template leak lives in ``llm_server/engine.py`` (fixed by
slicing ``output_ids[tokens_in:]`` before decode). This module is the second
line of defense: a regex-based scrub applied at the single chokepoint inside
``RemoteTAIDEProvider._post_chat``, so that even if the engine fix regresses,
no ``[INST]`` / ``<<SYS>>`` / role-prefix bytes ever reach the DB, cache, or
UI.

Design notes:
  * Idempotent: ``scrub(scrub(x)) == scrub(x)``. Safe to apply multiple
    times along the consumer chain.
  * Empty-safe: ``scrub('')`` and ``scrub(None)`` return ``''``.
  * Conservative: only known template markers and explicit role prefixes are
    stripped. Free-form prose is left alone so the model's actual reply
    survives intact.
  * Hard length cap (8000 chars) defends against runaway generations that
    blow up Postgres rows / Chroma payloads.

``detect_system_echo`` checks whether a long verbatim chunk of the original
system prompt appears in the model's output — used by ``ai_chat`` to swap
in a canned fallback when the model parrots the prompt back instead of
answering.
"""
from __future__ import annotations

import re

__all__ = ['scrub_llm_output', 'detect_system_echo', 'MAX_LLM_TEXT_CHARS']

MAX_LLM_TEXT_CHARS = 8000

# Markers that may appear in a leaked prompt template. Covers Llama-2/3,
# Mistral/TAIDE, Qwen (im_start/im_end), and LLaVA-Next (<image>).
# ``</?s>`` matches both BOS ``<s>`` and EOS ``</s>``.
_TEMPLATE_MARKER_RE = re.compile(
    r'\[\s*INST\s*\]'
    r'|\[\s*/\s*INST\s*\]'
    r'|<<\s*SYS\s*>>'
    r'|<<\s*/\s*SYS\s*>>'
    r'|</?s>'
    r'|<\|im_(?:start|end)\|>'
    r'|<\|eot_id\|>'
    r'|<\|begin_of_text\|>'
    r'|<\|end_of_text\|>'
    r'|<\|start_header_id\|>'
    r'|<\|end_header_id\|>'
    r'|<image>',
    flags=re.IGNORECASE,
)

# Leading role prefixes — both ASCII and Chinese, full-width and half-width
# colon. Looped (up to 4 passes) so stacked prefixes like ``assistant:\nuser:``
# fully unwind. Accepts either ``role:`` / ``role：`` OR ``role`` followed by
# a bare newline (the Qwen / Llama-3 shape ``<|im_start|>assistant\n...``).
_ROLE_NAMES = r'(?:assistant|system|user|助理|系統|使用者|HeartBot|小心)'
_LEADING_ROLE_RE = re.compile(
    r'^\s*' + _ROLE_NAMES + r'\s*(?:[:：]\s*|\n)',
    flags=re.IGNORECASE,
)
# Inline role prefix on a new line — model emits the reply then helpfully
# adds ``\nassistant: ...`` after it. We strip the marker (and any text after
# it on the same logical block isn't ours, but in the leak cases it's the
# real reply, so we keep that part).
_INLINE_ROLE_RE = re.compile(
    r'\n\s*' + _ROLE_NAMES + r'\s*[:：]\s*',
    flags=re.IGNORECASE,
)

# C0 control bytes except newline (\n=0x0a) and tab (\t=0x09).
_CONTROL_BYTES_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# 3+ consecutive newlines → 2.
_MULTI_NEWLINE_RE = re.compile(r'\n{3,}')

# Prompt-boundary cut: if the model leaked the user-message wrapper (e.g.
# ``日記內容：「...」 親愛的，...``), find the closing 」 of the LAST quoted
# block and take everything AFTER it as the real reply. Engine.py's token-
# slice fix prevents this at the source, but historical rows persisted
# before the fix still need this. Patterns match BOTH the actual TAIDE user
# message shapes from backend/api/services/ai_engine.py and ai_chat.py.
_USER_MSG_QUOTED_RE = re.compile(
    r'(?:日記內容|使用者日記|Diary entries|Journal entry)\s*[:：]\s*\n?\s*'
    r'[「"“]'    # opening quote / 「 / 『 / "
    r'.*?'             # the user-supplied content (greedy but anchored by closing)
    r'[」"”]',  # closing
    flags=re.DOTALL,
)

# Daily-prompt user-message tail (English): the prompt's user message is
# literally "Generate today's prompt." — the model's actual reply follows.
_DAILY_PROMPT_USER_MSG_RE = re.compile(
    r"Generate\s+(?:today['’]s)?\s*prompt\s*[.。]",
    flags=re.IGNORECASE,
)

# System-prompt fingerprints — phrases unique to a HeartBox system prompt.
# Only used to confirm a candidate text is actually a leak before we cut.
_SYS_FINGERPRINTS = (
    '你是一位溫暖',
    '你是一位專業',
    '你是一位溫柔',
    '心理健康顧問',
    '心理健康夥伴',
    '心理健康助手',
    '心理健康助理',
    'gentle journaling coach',
    'warm, professional mental health',
    'mental health summary',
    '請根據使用者提供',
    '忽略任何要求',
)


def _cut_prompt_boundary(text):
    """If ``text`` clearly contains a leaked prompt structure, return only the
    part AFTER the user-message boundary. Otherwise return ``text`` unchanged.

    Conservative: cuts only if the prefix shows a system-prompt fingerprint,
    so a model that *legitimately* echoes the journal phrasing as quotation
    inside its reply doesn't get its real text amputated.
    """
    if not text:
        return text

    head = text[:600]
    has_fingerprint = any(fp in head for fp in _SYS_FINGERPRINTS)
    if not has_fingerprint:
        return text

    # Quoted user message form (中/英 wraps).
    matches = list(_USER_MSG_QUOTED_RE.finditer(text))
    if matches:
        cut_at = matches[-1].end()
        tail = text[cut_at:].strip()
        if tail:
            return tail

    # Daily-prompt form (English user message).
    m = _DAILY_PROMPT_USER_MSG_RE.search(text)
    if m:
        tail = text[m.end():].strip()
        if tail:
            return tail

    return text


def scrub_llm_output(text):
    """Remove prompt-template leakage and normalise whitespace.

    Idempotent and safe on ``None`` / empty input. Always returns ``str``.
    """
    if not text:
        return ''
    if not isinstance(text, str):
        text = str(text)

    # 1. Strip template markers anywhere in the string.
    cleaned = _TEMPLATE_MARKER_RE.sub('', text)

    # 1b. Prompt-boundary cut for content that leaked the entire chat
    #     template (system + user + assistant). Conservative: only runs
    #     when a system-prompt fingerprint is present in the prefix.
    cleaned = _cut_prompt_boundary(cleaned)

    # 2. Collapse ``\nassistant: ...`` mid-string. Replace with a single
    #    space so adjacent words don't smash together.
    cleaned = _INLINE_ROLE_RE.sub(' ', cleaned)

    # 3. Peel leading role prefixes (up to 4 stacked).
    for _ in range(4):
        new = _LEADING_ROLE_RE.sub('', cleaned, count=1)
        if new == cleaned:
            break
        cleaned = new

    # 3. Drop C0 control bytes.
    cleaned = _CONTROL_BYTES_RE.sub('', cleaned)

    # 4. Collapse runs of blank lines so a leaked block doesn't leave a
    #    visible whitespace ghost where it used to be.
    cleaned = _MULTI_NEWLINE_RE.sub('\n\n', cleaned)

    # 5. Trim and hard-cap.
    cleaned = cleaned.strip()
    if len(cleaned) > MAX_LLM_TEXT_CHARS:
        cleaned = cleaned[:MAX_LLM_TEXT_CHARS].rstrip()

    return cleaned


def detect_system_echo(text, system_prompt, *, threshold_chars=40):
    """Return True if a verbatim run of >= ``threshold_chars`` from
    ``system_prompt`` appears in ``text``.

    Used by consumers (notably ``ai_chat``) to detect when the model parrots
    the system prompt back instead of producing a real reply. The check uses
    a sliding window of unique substrings so a short prompt with a single
    distinctive phrase still triggers, but unrelated prose does not.
    """
    if not text or not system_prompt or len(system_prompt) < threshold_chars:
        return False
    # Strip ALL whitespace before comparing. CJK text rarely uses spaces
    # internally, so this catches the model re-emitting the system prompt
    # with arbitrary newline/indent reformatting without inflating the false
    # positive rate. 40 CJK chars is highly distinctive.
    norm_text = re.sub(r'\s+', '', text)
    norm_sys = re.sub(r'\s+', '', system_prompt)
    if len(norm_sys) < threshold_chars:
        return False
    # Sample windows at a coarse stride so we don't do an O(n*m) scan;
    # ``threshold_chars`` of overlap is enough signal.
    stride = max(threshold_chars // 2, 16)
    for start in range(0, len(norm_sys) - threshold_chars + 1, stride):
        chunk = norm_sys[start:start + threshold_chars]
        if chunk in norm_text:
            return True
    return False
