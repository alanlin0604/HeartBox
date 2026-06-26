"""Analytics, calendar, alerts, year pixels, daily prompt, reviews,
self-assessments, and AI suggestion endpoints.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import random
import re
from datetime import timedelta

from django.core.cache import cache

from ..services.llm.sanitize import scrub_llm_output
from django.db.models import Avg
from django.utils import timezone

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    CounselorProfile, DailySleep, Habit, HabitLog,
    MoodNote, SelfAssessment, SharedAssessment,
)
from ..serializers import SelfAssessmentSerializer, SharedAssessmentSerializer
from ..services.analytics import (
    get_activity_mood_correlation, get_calendar_data, get_frequent_tags,
    get_gratitude_stats, get_mood_trends, get_mood_weather_correlation,
    get_personal_insights, get_sleep_mood_correlation, get_stress_by_tag,
    get_year_pixels,
)
from ..services.alerts import check_mood_alerts

from . import (
    CACHE_TTL_ANALYTICS, CACHE_TTL_CALENDAR, CACHE_TTL_DAILY_PROMPT,
    CACHE_TTL_YEAR_PIXELS, _get_llm_provider_or_none, _push_ws_notification,
    create_notification_if_enabled, error_response, logger,
)


class AnalyticsView(APIView):
    # Cache-key version bumped on every analytics schema addition so old
    # responses don't survive long enough to look broken to the user.
    #   v3 — default lookback 90 -> 180
    #   v4 — added personal_insights bundle field
    CACHE_KEY_VERSION = 'v4'

    def get(self, request):
        period = request.query_params.get('period', 'week')
        # Default lookback widened to 180 days. Even at 90d a casual
        # journaler often doesn't accumulate enough tagged notes to show
        # the "常用標籤" widget; 180d catches the long-tail without going
        # all the way to "lifetime" semantics. The auto-expand fallback
        # below stretches further (365d) if even 180d returns sparse.
        try:
            lookback_days = min(max(int(request.query_params.get('lookback_days', 180)), 1), 365)
        except (ValueError, TypeError):
            lookback_days = 180

        cache_key = f'analytics_{self.CACHE_KEY_VERSION}_{request.user.id}_{period}_{lookback_days}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)

        # Calculate streaks (cap to last 366 dates for performance)
        dates = list(
            qs.values_list('created_at__date', flat=True)
            .distinct()
            .order_by('-created_at__date')[:366]
        )
        current_streak = 0
        longest_streak = 0
        if dates:
            today = timezone.localdate()
            # Current streak: count consecutive days from today/yesterday
            streak = 0
            expected = today
            for d in dates:
                if d == expected:
                    streak += 1
                    expected = d - timezone.timedelta(days=1)
                elif d == today - timezone.timedelta(days=1) and streak == 0:
                    # Allow starting from yesterday if no entry today
                    streak = 1
                    expected = d - timezone.timedelta(days=1)
                else:
                    break
            current_streak = streak

            # Longest streak
            best = 1
            run = 1
            sorted_dates = sorted(set(dates))
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
            longest_streak = best

        gratitude = get_gratitude_stats(qs)

        # Auto-expand the lookback window when the requested span returned
        # an "all empty" analytics page. Users who write infrequently would
        # otherwise see a fully-empty dashboard for weeks; widening to up
        # to 365 days catches the long-tail correlations they HAVE recorded
        # without forcing them to manually fiddle with the query param.
        # Stops at the first span that produces ANY data.
        def _bundle(days):
            return {
                'mood_trends': get_mood_trends(qs, period=period, lookback_days=days),
                'weather_correlation': get_mood_weather_correlation(qs, lookback_days=days),
                'frequent_tags': get_frequent_tags(qs, lookback_days=days),
                'stress_by_tag': get_stress_by_tag(qs, lookback_days=days),
                'activity_correlation': get_activity_mood_correlation(qs, lookback_days=days),
                'sleep_correlation': get_sleep_mood_correlation(qs, lookback_days=days),
                'personal_insights': get_personal_insights(qs, lookback_days=days),
            }

        def _sample_size(block):
            """Returns the count of meaningful observations in a service-
            function result regardless of whether it shaped its return as
            ``{sample_size: int}`` (weather/sleep correlations) or as a
            plain ``list`` (frequent_tags, stress_by_tag, activity_correlation).
            """
            if isinstance(block, dict):
                return int(block.get('sample_size') or 0)
            if isinstance(block, list):
                return len(block)
            return 0

        def _is_sparse(b):
            """Treat the dashboard as 'no useful content' iff every analytic
            block came back empty / below-threshold. Gates the auto-expand
            fallback that widens the lookback window when a casual journaler
            wouldn't otherwise see any data."""
            return (
                _sample_size(b['frequent_tags']) == 0 and
                _sample_size(b['stress_by_tag']) == 0 and
                _sample_size(b['weather_correlation']) < 3 and
                _sample_size(b['sleep_correlation']) < 3 and
                _sample_size(b['activity_correlation']) < 3 and
                len(b.get('personal_insights') or []) == 0
            )

        bundle = _bundle(lookback_days)
        actual_lookback = lookback_days
        if _is_sparse(bundle):
            for fallback_days in (180, 365):
                if fallback_days <= lookback_days:
                    continue
                bigger = _bundle(fallback_days)
                if not _is_sparse(bigger):
                    bundle = bigger
                    actual_lookback = fallback_days
                    break

        result = {
            **bundle,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'gratitude_count': gratitude['gratitude_count'],
            'gratitude_streak': gratitude['gratitude_streak'],
            # Surface the actual window so the frontend can show
            # "showing last 365 days because no recent activity" hint.
            'actual_lookback_days': actual_lookback,
            'requested_lookback_days': lookback_days,
        }
        cache.set(cache_key, result, CACHE_TTL_ANALYTICS)
        return Response(result)


class MyProgressView(APIView):
    """Baseline-vs-current comparison so users can SEE that using HeartBox
    correlates with improvement. Added 2026-06-02 per thesis-advisor
    feedback ("the user should have a control group / before-after view").

    Baseline window: the FIRST 7 calendar days the user wrote any journal
    (or the first 7 days after account creation if there are no notes).
    Current window: the most recent 7 calendar days ending today.

    For each window we aggregate:
      - avg_sentiment    (MoodNote.sentiment_score, daily mean of means)
      - avg_stress       (MoodNote.stress_index, daily mean of means)
      - journal_days     (distinct dates with at least one note)
      - habit_completion (HabitLog rows / [active_habit × window_days])
      - avg_sleep_hours  (DailySleep.sleep_hours mean, if any rows)

    Returns null for metrics that have no baseline OR no current data so
    the frontend can render a friendly "not enough data yet" message
    instead of a misleading 0 → 0 delta.
    """

    def get(self, request):
        from datetime import timedelta
        from django.db.models import Avg, Count

        user = request.user
        today = timezone.localdate()

        # --- Find baseline window ---
        first_note_date = (
            MoodNote.objects.filter(user=user, is_deleted=False)
            .order_by('created_at')
            .values_list('created_at__date', flat=True)
            .first()
        )
        baseline_start = first_note_date or user.created_at.date()
        baseline_end = baseline_start + timedelta(days=6)

        current_end = today
        current_start = current_end - timedelta(days=6)

        # If the user hasn't been using HeartBox long enough to have a
        # baseline week distinct from the current week, return a sentinel
        # so the UI can show "keep using for 1 more week to unlock".
        if baseline_end >= current_start:
            return Response({
                'has_enough_data': False,
                'days_until_unlock': max(0, (current_start - baseline_end).days * -1),
                'baseline_start': baseline_start.isoformat(),
                'current_end': current_end.isoformat(),
            })

        def window_stats(start, end):
            note_qs = MoodNote.objects.filter(
                user=user, is_deleted=False,
                created_at__date__gte=start,
                created_at__date__lte=end,
            )
            agg = note_qs.aggregate(
                avg_sentiment=Avg('sentiment_score'),
                avg_stress=Avg('stress_index'),
            )
            journal_days = (
                note_qs.values_list('created_at__date', flat=True).distinct().count()
            )

            sleep_qs = DailySleep.objects.filter(user=user, date__gte=start, date__lte=end)
            sleep_agg = sleep_qs.aggregate(avg_hours=Avg('sleep_hours'))

            # Habit completion = total logs / (active habits × window days).
            # Clamped at 1.0 in case the user logs more than once per day.
            active_habits = Habit.objects.filter(user=user, is_active=True).count()
            window_days = (end - start).days + 1
            habit_logs = HabitLog.objects.filter(
                habit__user=user, date__gte=start, date__lte=end,
            ).count()
            denom = active_habits * window_days
            habit_completion = round(min(habit_logs / denom, 1.0), 3) if denom else None

            return {
                'window_start': start.isoformat(),
                'window_end': end.isoformat(),
                'avg_sentiment': round(agg['avg_sentiment'], 3) if agg['avg_sentiment'] is not None else None,
                'avg_stress':    round(agg['avg_stress'], 2)    if agg['avg_stress']    is not None else None,
                'journal_days':  journal_days,
                'avg_sleep_hours': round(sleep_agg['avg_hours'], 2) if sleep_agg['avg_hours'] is not None else None,
                'habit_completion': habit_completion,
            }

        baseline = window_stats(baseline_start, baseline_end)
        current = window_stats(current_start, current_end)

        # Deltas. Sign convention: positive = improvement.
        # sentiment ↑ is good, stress ↓ is good — we invert stress so a
        # positive delta always means "better".
        def safe_delta(curr, base, *, invert=False):
            if curr is None or base is None:
                return None
            d = curr - base
            return round(-d if invert else d, 3)

        deltas = {
            'avg_sentiment': safe_delta(current['avg_sentiment'], baseline['avg_sentiment']),
            'avg_stress':    safe_delta(current['avg_stress'],    baseline['avg_stress'], invert=True),
            'journal_days':  safe_delta(current['journal_days'],  baseline['journal_days']),
            'avg_sleep_hours': safe_delta(current['avg_sleep_hours'], baseline['avg_sleep_hours']),
            'habit_completion': safe_delta(current['habit_completion'], baseline['habit_completion']),
        }

        days_using = (today - baseline_start).days + 1

        return Response({
            'has_enough_data': True,
            'days_using': days_using,
            'baseline': baseline,
            'current': current,
            'deltas': deltas,
        })


class CalendarView(APIView):
    def get(self, request):
        try:
            year = int(request.query_params.get('year', timezone.now().year))
            month = int(request.query_params.get('month', timezone.now().month))
        except (ValueError, TypeError):
            return error_response('invalid_year_month', 'Invalid year or month.')
        if not (1 <= month <= 12) or not (1900 <= year <= 2100):
            return error_response('year_month_range', 'Year must be 1900-2100, month must be 1-12.')

        cache_key = f'calendar_{request.user.id}_{year}_{month}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        days = get_calendar_data(qs, year, month)
        result = {'year': year, 'month': month, 'days': days}
        cache.set(cache_key, result, CACHE_TTL_CALENDAR)
        return Response(result)


class AlertsView(APIView):
    def get(self, request):
        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        alerts = check_mood_alerts(qs)
        return Response({'alerts': alerts})


class YearPixelsView(APIView):
    def get(self, request):
        try:
            year = int(request.query_params.get('year', timezone.now().year))
        except (ValueError, TypeError):
            year = timezone.now().year

        cache_key = f'year_pixels_{request.user.id}_{year}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({'year': year, 'pixels': cached})

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        pixels = get_year_pixels(qs, year)
        cache.set(cache_key, pixels, CACHE_TTL_YEAR_PIXELS)
        return Response({'year': year, 'pixels': pixels})


# ===== Daily Prompt View =====

DEFAULT_PROMPTS_ZH = [
    # Sentence-starter shape: when the user clicks "使用此提示" the editor
    # is pre-filled with a sentence they can continue typing from instead
    # of staring at a question and a blank page. Mix in a few direct
    # questions for variety, but most should be openings.
    "今天我感謝的事是…",
    "讓我微笑的一個瞬間是…",
    "今天最讓我印象深刻的是…",
    "現在的我感覺…",
    "今天我學到的一件事是…",
    "今天和我有愉快互動的人是…",
    "我今天最想對自己說：",
    "現在身體告訴我的是…",
    "今天我為自己做的小事是…",
    "我最近感到驕傲的一件事是…",
    "今天超出我預期的是…",
    "如果可以重來今天，我會…",
    "我現在最需要的是…",
    "我最近擔心的是…",
    "上次我真正放鬆是在…",
    "今天遇到的挑戰是…，我這樣面對：",
    "今天的我可以用三個詞形容：",
    "我最想跟說話的人是…",
    "今天的小確幸：",
    "今天的天氣讓我聯想到…",
]

DEFAULT_PROMPTS_EN = [
    # Sentence-starter shape — see DEFAULT_PROMPTS_ZH note.
    "Today I'm grateful for…",
    "A moment that made me smile today was…",
    "What stood out most today was…",
    "Right now I'm feeling…",
    "One thing I learned today is…",
    "Someone who made today better was…",
    "Today I want to remind myself that…",
    "My body is telling me that…",
    "A small kindness I did for myself today was…",
    "Something I'm proud of lately is…",
    "What surprised me today was…",
    "If I could redo today, I would…",
    "What I need most right now is…",
    "What's been on my mind lately is…",
    "The last time I really relaxed was…",
    "Today's challenge: …  How I handled it: …",
    "Three words for me today:",
    "Someone I'd love to talk to right now is…",
    "Today's small joy:",
    "Today's weather makes me feel…",
]

DEFAULT_PROMPTS_JA = [
    # Sentence-starter shape — see DEFAULT_PROMPTS_ZH note.
    "今日感謝していることは…",
    "今日笑顔になった瞬間は…",
    "今日一番印象に残ったのは…",
    "今の私の気持ちは…",
    "今日学んだことは…",
    "今日嬉しい時間を過ごした相手は…",
    "今日自分に言いたいことは：",
    "体が今教えてくれているのは…",
    "今日自分にしてあげた小さなことは…",
    "最近誇りに思っていることは…",
    "今日予想外だったのは…",
    "もし今日をやり直せるなら…",
    "今一番必要なのは…",
    "最近気にかかっていることは…",
    "前回本当にリラックスできたのは…",
    "今日の挑戦：　その対処：",
    "今日の私を三つの言葉で：",
    "今話したい相手は…",
    "今日のささやかな幸せ：",
    "今日の天気が思い出させてくれるのは…",
]

DEFAULT_PROMPTS_MAP = {
    'zh-TW': DEFAULT_PROMPTS_ZH,
    'en': DEFAULT_PROMPTS_EN,
    'ja': DEFAULT_PROMPTS_JA,
}


# System-prompt fingerprints that should NEVER appear in a daily prompt.
# If any of these substrings is in the model output it means the model is
# parroting the system prompt back instead of generating a question.
_DAILY_PROMPT_FINGERPRINTS = (
    'journaling coach',
    'open-ended journaling prompt',
    'generate one',
    'average stress level',
    "mood score this week",
    '一位溫柔的',
    '日記教練',
)


def _sanitize_daily_prompt(raw, *, mood_avg=None, stress_avg=None):
    """Clean a generated daily prompt. Returns the cleaned string, or ``None``
    if the output should be rejected and fallback used.

    Rejection criteria (a daily prompt should be ONE short question that the
    user can act on immediately; anything longer is friction not a prompt):
      * scrub leaves empty / template-only text
      * length > 80 chars after strip (real CJK question is ~15-30 chars)
      * length < 6 chars (model hallucinated a fragment)
      * more than ONE question mark — 連問 = not actionable
      * contains a newline (multi-paragraph prose, not a prompt)
      * contains an instruction shape ("請寫下" + further clause / "花十分鐘" /
        "獨自一人" — those are coaching essays, not journal prompts)
      * contains a system-prompt fingerprint
      * contains the mood/stress numeric strings injected into the system prompt
    """
    if not raw:
        return None
    cleaned = scrub_llm_output(raw)
    if not cleaned:
        return None
    # Strip wrapping quotes / 「」 / 『』 / 「」 / 『 the model often adds.
    cleaned = cleaned.strip().strip('"\'').strip('「」『』').strip()
    if not cleaned:
        return None
    # Tight bounds — a 1-line question. Previous 200-char cap allowed the
    # TAIDE "獨自一人在自然環境中觀察並傾聽自己的內心..." essay to slip through.
    if len(cleaned) > 80 or len(cleaned) < 6:
        return None
    # Reject newlines outright (was: only blank-line pairs).
    if '\n' in cleaned or '\r' in cleaned:
        return None
    # Multi-question rejection: a prompt must contain AT MOST one ？/?
    qmark_count = cleaned.count('？') + cleaned.count('?')
    if qmark_count > 1:
        return None
    lowered = cleaned.lower()
    if any(fp in lowered for fp in _DAILY_PROMPT_FINGERPRINTS):
        return None
    # Reject essay-shape instructions that pretend to be a question.
    essay_markers = ('花十分鐘', '花十分钟', '獨自一人', '獨自一個',
                     '寫下關於', '寫下你對', '讓內在', '療癒的指南')
    if any(m in cleaned for m in essay_markers):
        return None
    # Numeric fingerprints from the system prompt's mood_ctx.
    if mood_avg is not None and f'{mood_avg:.2f}' in cleaned:
        return None
    if stress_avg is not None and f'{stress_avg:.1f}' in cleaned:
        return None
    return cleaned


# Short TTL for fallback prompts so one bad day doesn't pin the cache for 24h.
CACHE_TTL_DAILY_PROMPT_FALLBACK = 600


class PersonalSuggestionView(APIView):
    """LLM-generated daily wellness paragraph for the journal page.

    POST body: {lat, lon} (client browser geolocation, or Taipei fallback).
    Response: {paragraph, weather, triggers, fallback_used}.

    Result cached per (user, day, ~10km grid, lang) for 12h on success and
    10min when the LLM declined / failed, so a transient outage doesn't
    pin the cache for the whole day.
    """
    CACHE_KEY_VERSION = 'v1'

    def post(self, request):
        from datetime import date as date_cls
        from ..services.personal_suggestion import (
            compute_triggers, fetch_today_weather, generate_paragraph_zh,
        )

        try:
            lat = float(request.data.get('lat', 25.0478))
            lon = float(request.data.get('lon', 121.5319))
        except (TypeError, ValueError):
            return error_response('invalid_coords', 'lat/lon must be numbers', 400)

        # Round to ~10km grid for cache locality + privacy (we never log exact coords)
        lat_k = round(lat, 1)
        lon_k = round(lon, 1)
        today = date_cls.today()
        lang = request.headers.get('Accept-Language', 'zh-TW')

        cache_key = (
            f'personal_sugg_{self.CACHE_KEY_VERSION}_{request.user.id}_'
            f'{today.isoformat()}_{lat_k}_{lon_k}_{lang}'
        )
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Weather cached separately by grid (1h) so multiple users in the
        # same area share one Open-Meteo fetch
        weather_key = f'weather_{today.isoformat()}_{lat_k}_{lon_k}'
        weather = cache.get(weather_key)
        if weather is None:
            weather = fetch_today_weather(lat, lon)
            if weather:
                cache.set(weather_key, weather, 3600)

        qs = MoodNote.objects.filter(user=request.user, is_deleted=False)
        insights = get_personal_insights(qs, lookback_days=180)

        triggers = compute_triggers(insights, weather, today)

        paragraph = None
        if lang == 'zh-TW':
            paragraph = generate_paragraph_zh(insights, weather, today, triggers)

        response_data = {
            'paragraph': paragraph,
            'weather': weather,
            'triggers': triggers,
            'fallback_used': paragraph is None,
        }
        # 12h on success so the same user hitting the page twice in a day
        # gets the same coherent suggestion; 10min on fallback so a TAIDE
        # blip doesn't pin a bad/missing paragraph.
        ttl = 43200 if paragraph else 600
        cache.set(cache_key, response_data, ttl)
        return Response(response_data)


class DailyPromptView(APIView):
    # Cache-key version bumped to invalidate any historical entries when the
    # validator rules tighten. Bump again on future format changes so old
    # cache rows die naturally.
    #   v2 -- post-prompt-template-leak fix (wf_ba1ab074-010)
    #   v3 -- post-essay-prompt rejection (stricter validator: <=80 chars,
    #         1 question mark max, no essay markers)
    CACHE_KEY_VERSION = 'v3'

    def get(self, request):
        today = timezone.now().date().isoformat()
        cache_key = f'daily_prompt_{self.CACHE_KEY_VERSION}_{request.user.id}_{today}'
        cached = cache.get(cache_key)
        if cached:
            return Response({'prompt': cached})

        # Generate prompt based on recent mood
        prompt_text = None
        avg_s = avg_st = None
        try:
            recent = MoodNote.objects.filter(
                user=request.user,
                is_deleted=False,
                sentiment_score__isnull=False,
                created_at__gte=timezone.now() - timedelta(days=7),
            ).aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

            avg_s = recent['avg_s']
            avg_st = recent['avg_st']

            provider = _get_llm_provider_or_none()
            if provider:
                lang = request.headers.get('Accept-Language', 'zh-TW')
                lang_map = {'zh-TW': 'Traditional Chinese', 'en': 'English', 'ja': 'Japanese'}
                lang_name = lang_map.get(lang, 'Traditional Chinese')
                mood_ctx = ''
                if avg_s is not None:
                    mood_ctx = f"The user's average mood score this week is {avg_s:.2f} (scale -1 to 1). "
                if avg_st is not None:
                    mood_ctx += f"Average stress level is {avg_st:.1f}/10. "

                raw = provider.chat(
                    system=(
                        f'You are a gentle journaling coach. {mood_ctx}'
                        f'Generate ONE short question in {lang_name} that the user '
                        f'can start answering in their journal within 5 seconds.\n\n'
                        f'STRICT RULES:\n'
                        f'  - Output MUST be a single question, ending with one ? or ？\n'
                        f'  - Maximum 25 Chinese characters / 15 English words.\n'
                        f'  - NO instructions like "花十分鐘", "獨自一人", "寫下".\n'
                        f'  - NO multi-part / compound questions joined by "and" or "，"\n'
                        f'  - NO quotes, labels, prefixes, explanations.\n'
                        f'  - Example shape: "今天最讓你感謝的一件事是什麼？" / '
                        f'"What surprised you today?" / "今は何が必要ですか？"'
                    ),
                    user='Generate today’s prompt.',
                    max_tokens=40,
                    temperature=0.7,
                    timeout=15,
                )
                prompt_text = _sanitize_daily_prompt(
                    raw, mood_avg=avg_s, stress_avg=avg_st,
                )
                if prompt_text is None:
                    logger.warning(
                        'daily_prompt sanitize_rejected raw_len=%d',
                        len(raw or ''),
                    )
        except Exception as e:
            logger.warning('Daily prompt generation failed: %s', e)

        used_fallback = False
        if not prompt_text:
            lang = request.headers.get('Accept-Language', 'zh-TW')
            prompts = DEFAULT_PROMPTS_MAP.get(lang, DEFAULT_PROMPTS_ZH)
            prompt_text = random.choice(prompts)
            used_fallback = True

        # Short TTL for fallback so a degraded LLM doesn't pin the cache for
        # 24h. Successful AI generations get the full TTL.
        ttl = CACHE_TTL_DAILY_PROMPT_FALLBACK if used_fallback else CACHE_TTL_DAILY_PROMPT
        cache.set(cache_key, prompt_text, ttl)
        return Response({'prompt': prompt_text})


class JournalStreakView(APIView):
    """Get user's current journaling streak information."""

    def get(self, request):
        from api.services.streaks import update_streak
        from ..serializers import JournalStreakSerializer
        # Always recalculate to ensure accuracy
        streak = update_streak(request.user)
        serializer = JournalStreakSerializer(streak)
        return Response(serializer.data)


class MonthlyReviewView(APIView):
    """Get monthly review with statistics and highlights."""

    def get(self, request):
        from api.services.reviews import get_monthly_review

        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response({'error': 'year and month parameters are required'}, status=400)

        try:
            year = int(year)
            month = int(month)
            if not (1 <= month <= 12):
                raise ValueError('Month must be between 1 and 12')
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        review = get_monthly_review(request.user, year, month)
        if not review:
            return Response({'error': 'No notes found for this month'}, status=404)

        return Response(review)


class YearlyReviewView(APIView):
    """Get yearly review (Year in Review) with comprehensive statistics."""

    def get(self, request):
        from api.services.reviews import get_yearly_review

        year = request.query_params.get('year')
        if not year:
            # Default to current year
            year = timezone.now().year
        else:
            try:
                year = int(year)
            except ValueError:
                return Response({'error': 'Invalid year'}, status=400)

        review = get_yearly_review(request.user, year)
        if not review:
            return Response({'error': 'No notes found for this year'}, status=404)

        return Response(review)


class AISuggestionsView(APIView):
    """Get AI-powered writing suggestions, insights, and reflection questions."""

    def get(self, request):
        from api.services.ai_suggestions import get_ai_suggestions

        try:
            suggestions = get_ai_suggestions(request.user)
            return Response(suggestions)
        except Exception as e:
            logger.error(f'Failed to generate AI suggestions for user {request.user.pk}: {e}')
            return Response({'error': 'Failed to generate suggestions'}, status=500)


class MoodPredictionView(APIView):
    """Get mood and stress predictions with health tips."""

    def get(self, request):
        from api.services.predictions import get_mood_prediction, get_health_tips

        try:
            prediction = get_mood_prediction(request.user)
            health_tips = get_health_tips(request.user)

            return Response({
                'prediction': prediction,
                'health_tips': health_tips,
                'generated_at': timezone.now().isoformat()
            })
        except Exception as e:
            logger.error(f'Failed to generate mood prediction for user {request.user.pk}: {e}')
            return Response({'error': 'Failed to generate prediction'}, status=500)


class SelfAssessmentListCreateView(generics.ListCreateAPIView):
    serializer_class = SelfAssessmentSerializer

    def get_queryset(self):
        qs = SelfAssessment.objects.filter(user=self.request.user)
        atype = self.request.query_params.get('type')
        if atype in ('phq9', 'gad7'):
            qs = qs.filter(assessment_type=atype)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ShareAssessmentView(APIView):
    """Share a self-assessment result with a counselor."""

    def post(self, request, pk):
        from rest_framework import status
        try:
            assessment = SelfAssessment.objects.get(pk=pk, user=request.user)
        except SelfAssessment.DoesNotExist:
            return error_response('assessment_not_found', 'Assessment not found.', 404)

        counselor_id = request.data.get('counselor_id')
        if not counselor_id:
            return error_response('counselor_id_required', 'counselor_id is required.')

        # Verify target is an approved counselor
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            try:
                profile = CounselorProfile.objects.get(user_id=counselor_id, status='approved')
            except CounselorProfile.DoesNotExist:
                return error_response('counselor_not_approved', 'Counselor not found or not approved.', 404)

        shared, created = SharedAssessment.objects.get_or_create(
            assessment=assessment,
            shared_with=profile.user,
        )
        if not created:
            return error_response('already_shared', 'Already shared with this counselor.', 200)

        # Notify counselor
        notif = create_notification_if_enabled(
            profile.user, 'share',
            title='Assessment shared',
            message=f'{request.user.username} shared a {assessment.assessment_type.upper()} assessment with you.',
            data={
                'assessment_id': assessment.id,
                'assessment_type': assessment.assessment_type,
                'username': request.user.username,
            },
        )
        if notif:
            _push_ws_notification(profile.user_id, notif)

        return Response(SharedAssessmentSerializer(shared).data, status=status.HTTP_201_CREATED)


class SharedAssessmentsReceivedView(generics.ListAPIView):
    """Counselor endpoint to list assessments shared with them."""
    serializer_class = SharedAssessmentSerializer

    def get_queryset(self):
        return SharedAssessment.objects.filter(
            shared_with=self.request.user,
        ).select_related('assessment', 'assessment__user')
