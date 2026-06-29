"""LLM-backed "today's personalised suggestion" for the journal page.

Stitches together three signals into one short, warm paragraph:

  1. Long-term mood patterns from ``get_personal_insights``
     (best/worst month, weekday vs weekend, etc.)
  2. Today's local weather from Open-Meteo (no API key, free tier)
  3. The cross-referenced triggers for *today* — e.g. "today is a
     weekend, and weekends are historically your lower side"

Then asks the local TAIDE chat model for a 2-3 sentence Traditional
Chinese paragraph in a warm-friend tone. Returns ``None`` when the LLM
isn't configured / errors / produces something out of length bounds, so
the caller can fall back to the React template tips it already renders.

Only Traditional Chinese is generated server-side — TAIDE-LX-7B is a
TW-focused model and quality on en/ja would be inconsistent. Other
languages should use the static React templates.
"""
from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Optional

import httpx

from .llm.factory import get_llm_provider
from .llm.base import LLMProviderError

logger = logging.getLogger(__name__)

# WMO weather codes -> coarse bucket used in our copy
WMO_BUCKET = {
    0: 'clear', 1: 'clear',
    2: 'cloudy', 3: 'cloudy',
    45: 'fog', 48: 'fog',
    51: 'rain', 53: 'rain', 55: 'rain',
    56: 'rain', 57: 'rain',
    61: 'rain', 63: 'rain', 65: 'rain',
    66: 'rain', 67: 'rain',
    71: 'snow', 73: 'snow', 75: 'snow', 77: 'snow',
    80: 'rain', 81: 'rain', 82: 'rain',
    85: 'snow', 86: 'snow',
    95: 'storm', 96: 'storm', 99: 'storm',
}

BUCKET_LABEL_ZH = {
    'clear': '晴朗', 'cloudy': '多雲', 'fog': '起霧',
    'rain': '有雨', 'snow': '下雪', 'storm': '雷雨',
}


def fetch_today_weather(lat: float, lon: float) -> Optional[dict]:
    """Returns ``{code, bucket, tempMax, tempMin, tempNow}`` or ``None``."""
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': f'{lat:.4f}',
        'longitude': f'{lon:.4f}',
        'current': 'temperature_2m,weather_code',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min',
        'timezone': 'auto',
        'forecast_days': 1,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning('open_meteo fetch_failed lat=%s lon=%s err=%s', lat, lon, e)
        return None

    daily = data.get('daily') or {}
    current = data.get('current') or {}
    try:
        code = (daily.get('weather_code') or [None])[0]
        if code is None:
            code = current.get('weather_code', 0)
        code = int(code or 0)
        return {
            'code': code,
            'bucket': WMO_BUCKET.get(code, 'cloudy'),
            'tempMax': (daily.get('temperature_2m_max') or [None])[0],
            'tempMin': (daily.get('temperature_2m_min') or [None])[0],
            'tempNow': current.get('temperature_2m'),
        }
    except (TypeError, ValueError) as e:
        logger.warning('open_meteo bad_shape err=%s', e)
        return None


def _phase_of(day: int) -> str:
    if day <= 10:
        return 'early'
    if day <= 20:
        return 'mid'
    return 'late'


PHASE_LABEL_ZH = {'early': '月初（1-10號）', 'mid': '月中（11-20號）', 'late': '月底（21號之後）'}


def compute_triggers(
    insights: Optional[list[dict]],
    weather: Optional[dict],
    today: date_cls,
) -> list[str]:
    """Plain-Chinese sentences listing today's notable cross-references.

    Used both as LLM prompt context AND as a debug-able view of what fired.
    """
    triggers: list[str] = []
    if not weather:
        weather = {}

    bucket = weather.get('bucket')
    tmax = weather.get('tempMax')
    tmin = weather.get('tempMin')

    if bucket == 'rain':
        triggers.append('今天預報下雨')
    elif bucket == 'storm':
        triggers.append('今天預報雷雨')
    elif bucket == 'snow':
        triggers.append('今天預報下雪')

    if isinstance(tmax, (int, float)) and tmax >= 32:
        triggers.append(f'今天最高 {tmax:.0f}°C（偏熱）')
    if isinstance(tmin, (int, float)) and tmin <= 12:
        triggers.append(f'今天最低 {tmin:.0f}°C（偏涼）')

    day = today.day
    phase = _phase_of(day)
    dow = today.weekday()  # 0=Mon
    is_weekend = dow >= 5
    today_side = 'weekend' if is_weekend else 'weekday'
    today_side_zh = '週末' if is_weekend else '平日'
    month = today.month
    if isinstance(tmax, (int, float)) and isinstance(tmin, (int, float)):
        tavg = (tmax + tmin) / 2
    else:
        tavg = 24.0  # neutral midpoint if weather unavailable

    for ins in insights or []:
        k = ins.get('key')
        if k == 'month_phase' and ins.get('worst_phase') == phase:
            triggers.append(
                f'今天落在 {PHASE_LABEL_ZH.get(phase, phase)}，你過去這時段心情通常較低'
            )
        elif k == 'weekday_weekend':
            better = ins.get('better')
            if better and better != today_side:
                triggers.append(
                    f'今天是{today_side_zh}，你過去{today_side_zh}心情通常較低'
                )
        elif k == 'month_extremes' and ins.get('worst_month') == month:
            triggers.append(f'{month} 月是你過去心情最低的月份')
        elif k == 'weather_sun_rain' and bucket == 'rain' and ins.get('better') == 'sunny':
            triggers.append('你過去雨天心情通常比晴天低')
        elif k == 'temperature_band':
            better = ins.get('better')
            if better == 'warm' and tavg < 20:
                triggers.append('今天偏涼，而你過去暖天心情較好')
            elif better == 'cold' and tavg >= 25:
                triggers.append('今天偏熱，而你過去涼天心情較好')

    return triggers


def _insights_summary_zh(insights: Optional[list[dict]]) -> str:
    """Summarise long-term mood patterns WITHOUT exposing raw month numbers
    or month-phase labels to the LLM.

    Why no months/phases: TAIDE-LX-7B confidently misinterprets a literal
    "4 月最好" as "今天即將進入 4 月" or "六月中" gets read as "month
    phase 月中" referring to today. Both happen ~30% of the time on this
    model. Cross-references against today's date are already resolved in
    ``compute_triggers`` (which the LLM sees separately as a list of
    today-grounded statements), so this summary only needs to describe
    the dimension at a high level — not feed the model raw numerics it
    will confuse with the current date.
    """
    if not insights:
        return '尚無明顯規律'
    lines = []
    for ins in insights:
        k = ins.get('key')
        try:
            if k == 'weekday_weekend':
                better_zh = '週末' if ins['better'] == 'weekend' else '平日'
                lines.append(f"{better_zh}心情通常較好")
            elif k == 'weather_sun_rain':
                better_zh = '晴天' if ins['better'] == 'sunny' else '雨天'
                lines.append(f"{better_zh}心情通常較好")
            elif k == 'temperature_band':
                better_zh = '溫暖天氣' if ins['better'] == 'warm' else '涼爽天氣'
                lines.append(f"{better_zh}心情通常較好")
            # NOTE: month_phase + month_extremes are deliberately omitted.
            # Their cross-reference against today's date is generated in
            # compute_triggers() as a today-grounded sentence; the raw
            # "4 月 / 月初" labels confuse the model and produce
            # hallucinated dates in the output paragraph.
        except (KeyError, TypeError, ValueError):
            continue
    return '；'.join(lines) if lines else '尚無明顯規律'


def _weather_string_zh(weather: Optional[dict]) -> str:
    if not weather:
        return '無天氣資料'
    bucket_label = BUCKET_LABEL_ZH.get(weather.get('bucket'), '不明')
    tmax = weather.get('tempMax')
    tmin = weather.get('tempMin')
    tnow = weather.get('tempNow')
    parts = [bucket_label]
    if isinstance(tmin, (int, float)) and isinstance(tmax, (int, float)):
        parts.append(f'{tmin:.0f}-{tmax:.0f}°C')
    if isinstance(tnow, (int, float)):
        parts.append(f'目前 {tnow:.0f}°C')
    return '，'.join(parts)


DOW_ZH = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']


def generate_paragraph_zh(
    insights: Optional[list[dict]],
    weather: Optional[dict],
    today: date_cls,
    triggers: list[str],
) -> Optional[str]:
    """Calls TAIDE for a 2-3 sentence paragraph. Returns None on any failure."""
    try:
        provider = get_llm_provider()
        if not provider.is_configured():
            return None
    except LLMProviderError:
        return None

    weather_str = _weather_string_zh(weather)
    insights_str = _insights_summary_zh(insights)
    if triggers:
        triggers_str = '\n'.join(f'- {t}' for t in triggers)
    else:
        triggers_str = '- 今天沒有特別需要留意的情況'

    date_str = f'{today.year} 年 {today.month} 月 {today.day} 日（{DOW_ZH[today.weekday()]}）'

    try:
        text = provider.chat(
            system=(
                '你是 HeartBox 心事盒 App 的暖心建議助理，扮演一位關心使用者的好朋友。\n'
                '請根據今日資訊，寫一段「今日個人化建議」。\n\n'
                '嚴格規則（違反會被拒絕）：\n'
                '- 必須用繁體中文。\n'
                '- 只寫一段，60-120 個字，2 到 3 句。\n'
                '- 不要分多段、不要寫兩段相似的內容。\n'
                '- 不要用「親愛的」「各位」「使用者」這種稱呼開頭，直接從建議本身開始。\n'
                '- 不要寫「根據資料」「統計顯示」「分析結果」這類分析句。\n'
                '- 不要列點、不要 emoji、不要前言或後綴。\n'
                '- 語氣溫暖、像朋友在說話，避免冷冰冰的告知句。\n'
                '- 內容只能談「今天」，絕對不要提到其他月份、其他日子、「明天」、「昨天」、「上週」、「下週」、「即將」等時間詞。\n'
                '- 不要提到「月初」「月中」「月底」這類分段，也不要說「X 月」（除了今天所在的月份）。\n'
                '- 如果今天有需要留意的情況，請自然地把它融入句子裡（不要照抄條列）。'
            ),
            user=(
                f'今天：{date_str}\n'
                f'今天天氣：{weather_str}\n\n'
                f'使用者長期習慣（高層次，不要照抄）：\n{insights_str}\n\n'
                f'今天需要關注的情況：\n{triggers_str}\n\n'
                '請寫一段給使用者的「今日」暖心建議（只一段，60-120 字，只談今天）。'
            ),
            temperature=0.75,
            max_tokens=110,
            timeout=60,
        )
        text = (text or '').strip()
        text = _strip_duplicate_paragraphs(text)
        # Length sanity. TAIDE occasionally returns the prompt back or a
        # one-word reply on degenerate inputs — drop both.
        if len(text) < 20 or len(text) > 250:
            logger.warning('personal_suggestion length_reject len=%d', len(text))
            return None
        # Date/time hallucination check. TAIDE freely fabricates dates from
        # the insights data ("即將進入 4 月", "明天雖然是雷雨天") — both make
        # the widget look broken to the user. Reject any paragraph that:
        #   (a) mentions a month OTHER than today's month, OR
        #   (b) uses forbidden relative time words (明天/昨天/上週/下週/即將/月初/月中/月底).
        if _has_date_hallucination(text, today.month, today.weekday()):
            logger.warning(
                'personal_suggestion date_hallucination_reject text=%r',
                text[:120],
            )
            return None
        # Drop the model's repeated date prefix. The widget header already
        # shows "6月30日 · 雷雨 · 25°/32°C" right above the paragraph, so a
        # paragraph that starts "今天是 2026 年 6 月 30 日，週二。" is pure
        # duplication. Strip the leading "今天是 X 年 X 月 X 日（週N）。" /
        # "X 月 X 日（週N），..." patterns so the suggestion lands on the
        # first content sentence.
        text = _strip_date_prefix(text)
        return text
    except LLMProviderError as e:
        logger.warning('personal_suggestion llm_call failed: %s', e)
        return None


# Forbidden relative-time markers. Any of these in the paragraph means the
# model drifted off "today" — reject. Curated to avoid common false positives:
# we do NOT block "下次"/"上次" (refer to events, not days), "未來"/"以後"
# (vague future tense is fine), or "之前"/"接下來" (sentence flow words).
_FORBIDDEN_TIME_WORDS = (
    '明天', '後天', '昨天', '前天',
    '上週', '下週', '上周', '下周',
    '即將進入', '即將迎來', '即將到來', '即將到', '即將來臨',
    '邁到週末', '邁到周末', '邁向週末', '邁向周末',
    '月初', '月中', '月底',
    '最後一周', '最後一週', '本周末', '本週末',
)


def _has_date_hallucination(text: str, today_month: int, today_weekday: int = -1) -> bool:
    """Return True if the paragraph likely hallucinated a date that isn't today.

    Three checks:
      1. Any forbidden relative-time word from _FORBIDDEN_TIME_WORDS appears.
      2. Any month NUMBER other than today's appears (matches '4 月' / '4月').
      3. Weekday/weekend mismatch: today is a weekday (Mon-Fri) but the text
         calls today the weekend, OR today IS the weekend but the text calls
         today a weekday. Only triggers when the word appears within ~12
         chars of "今天" / "今日" so we don't flag legitimate historical
         comparisons like "你週末心情通常較好".
    """
    if not text:
        return False
    # Check (1): forbidden relative-time words anywhere
    for w in _FORBIDDEN_TIME_WORDS:
        if w in text:
            return True
    import re
    # Check (2): wrong-month numerals
    for m in re.finditer(r'(\d{1,2})\s*月', text):
        try:
            mo = int(m.group(1))
        except ValueError:
            continue
        if 1 <= mo <= 12 and mo != today_month:
            return True
    # Check (3): weekday/weekend mismatch *near* "今天"/"今日"
    if today_weekday >= 0:
        is_weekend = today_weekday >= 5  # 5=Sat, 6=Sun
        opposite_word = '平日' if is_weekend else '週末'
        # ~12 chars window before or after "今天" / "今日"
        for m in re.finditer(r'今[天日]', text):
            start = max(0, m.start() - 12)
            end = min(len(text), m.end() + 12)
            window = text[start:end]
            if opposite_word in window:
                return True
    return False


def _strip_date_prefix(text: str) -> str:
    """Remove the model's tendency to start with "今天是 X 年 X 月 X 日（週N）。"
    or similar date-restating openers. The widget already shows the date right
    above the paragraph; repeating it eats 15-30 of our 60-120 char budget.
    """
    if not text:
        return text
    import re
    # Patterns observed in real TAIDE outputs:
    #   "今天是 2026 年 6 月 30 日，週二。雖然..."
    #   "今天是 2026 年 6 月 30 日（週二），..."
    #   "6 月 30 日（週二），..."
    #   "今天 6 月 30 日 雷雨，..."
    # 週N marker after 日 is optional and may be wrapped in parens OR preceded
    # by a comma ("日，週二") — both shapes appear in real TAIDE outputs.
    _DOW = r'(?:\s*[，,]?\s*[（(]?週[一二三四五六日]?[）)]?)?'
    _TAIL = r'\s*[，,。.]?\s*'
    patterns = (
        r'^\s*今天是?\s*\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日' + _DOW + _TAIL,
        r'^\s*\d{1,2}\s*月\s*\d{1,2}\s*日' + _DOW + _TAIL,
        r'^\s*今天是?\s*\d{1,2}\s*月\s*\d{1,2}\s*日' + _DOW + _TAIL,
    )
    for pat in patterns:
        new = re.sub(pat, '', text, count=1)
        if new != text:
            text = new
            break
    return text.lstrip(' \n，。、；')


def _strip_duplicate_paragraphs(text: str) -> str:
    """Normalise TAIDE output: drop duplicate paragraphs AND strip the
    forbidden '親愛的XX，' / '各位XX，' / '使用者XX，' leading greeting.

    Strategies (composed in order; later ones see the trimmed result):
      1. If text has multiple paragraphs (split on blank line), keep the
         first non-trivial one.
      2. If the same intro word ('親愛的', '今天') appears more than once
         in close proximity, cut at the second occurrence.
      3. Even a SINGLE leading '親愛的好友，' / '各位讀者，' / '使用者，'
         gets stripped — the system prompt forbids these greetings, but
         TAIDE-LX-7B emits them anyway ~90% of the time. We keep the rest
         of the sentence intact so the suggestion starts on the real content.
    """
    if not text:
        return text

    import re
    # Strategy 1: keep only the first non-trivial paragraph
    parts = re.split(r'\n\s*\n', text)
    parts = [p.strip() for p in parts if len(p.strip()) >= 20]
    if len(parts) > 1:
        text = parts[0]

    # Strategy 2: detect repeated greeting patterns
    for pattern in (r'親愛的[好朋友者使用]', r'^今天在'):
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        if len(matches) > 1:
            text = text[:matches[1].start()].rstrip(' \n，。、；')
            break

    # Strategy 3: strip a SINGLE forbidden leading greeting (system prompt
    # says no '親愛的' / '各位' / '使用者' opener, but TAIDE still emits one).
    # Bound the post-keyword run at 0-8 non-punct chars so we don't eat into
    # real content, and require a trailing comma/colon so we never strip a
    # word that legitimately starts a sentence.
    text = re.sub(
        r'^\s*(?:親愛的|各位|使用者)[^，,。.\n！!？?]{0,8}[，,：:]\s*',
        '',
        text,
    )

    return text
