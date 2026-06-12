"""Analytics, calendar, alerts, year pixels, daily prompt, reviews,
self-assessments, and AI suggestion endpoints.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import random
from datetime import timedelta

from django.core.cache import cache
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
    get_sleep_mood_correlation, get_stress_by_tag, get_year_pixels,
)
from ..services.alerts import check_mood_alerts

from . import (
    CACHE_TTL_ANALYTICS, CACHE_TTL_CALENDAR, CACHE_TTL_DAILY_PROMPT,
    CACHE_TTL_YEAR_PIXELS, _get_openai_client, _push_ws_notification,
    create_notification_if_enabled, error_response, logger,
)


class AnalyticsView(APIView):
    def get(self, request):
        period = request.query_params.get('period', 'week')
        try:
            lookback_days = min(max(int(request.query_params.get('lookback_days', 30)), 1), 365)
        except (ValueError, TypeError):
            lookback_days = 30

        cache_key = f'analytics_{request.user.id}_{period}_{lookback_days}'
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

        result = {
            'mood_trends': get_mood_trends(qs, period=period, lookback_days=lookback_days),
            'weather_correlation': get_mood_weather_correlation(qs, lookback_days=lookback_days),
            'frequent_tags': get_frequent_tags(qs, lookback_days=lookback_days),
            'stress_by_tag': get_stress_by_tag(qs, lookback_days=lookback_days),
            'activity_correlation': get_activity_mood_correlation(qs, lookback_days=lookback_days),
            'sleep_correlation': get_sleep_mood_correlation(qs, lookback_days=lookback_days),
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'gratitude_count': gratitude['gratitude_count'],
            'gratitude_streak': gratitude['gratitude_streak'],
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
    "今天的心情如何？",
    "最近有什麼讓你開心的小事嗎？",
    "今天最想對自己說的一句話是什麼？",
    "此刻你的身體感覺如何？",
    "今天有什麼讓你印象深刻的事？",
    "最近有什麼讓你感到感恩的事嗎？",
    "今天遇到了什麼挑戰？你怎麼面對的？",
    "現在最想做的一件事是什麼？",
    "今天和誰有了愉快的互動？",
    "用三個詞形容你現在的狀態。",
    "今天學到了什麼新東西？",
    "如果可以重來，今天你會做什麼不同的事？",
    "最近什麼事情讓你感到驕傲？",
    "今天有沒有一個讓你微笑的瞬間？",
    "你現在最需要什麼？",
    "今天有什麼事情超出你的預期？",
    "最近有什麼讓你擔心的事嗎？",
    "你上次真正放鬆是什麼時候？",
    "如果此刻可以跟任何人說話，你會選誰？",
    "今天你為自己做了什麼好事？",
]

DEFAULT_PROMPTS_EN = [
    "How are you feeling right now?",
    "What's something small that made you happy recently?",
    "What would you say to yourself today?",
    "How does your body feel at this moment?",
    "What stood out to you today?",
    "What's something you feel grateful for recently?",
    "What challenge did you face today? How did you handle it?",
    "What's one thing you'd like to do for yourself right now?",
    "Who did you enjoy spending time with today?",
    "Describe your current state in three words.",
    "What did you learn today?",
    "If you could redo today, what would you do differently?",
    "What have you felt proud of recently?",
    "Was there a moment today that made you smile?",
    "What do you need most right now?",
    "What surprised you today?",
    "Is there something that's been worrying you lately?",
    "When was the last time you truly relaxed?",
    "If you could talk to anyone right now, who would it be?",
    "What's one kind thing you did for yourself today?",
]

DEFAULT_PROMPTS_JA = [
    "今日の気分はどうですか？",
    "最近、嬉しかった小さなことはありますか？",
    "今日、自分に言いたい一言は？",
    "今、体はどんな感じですか？",
    "今日、印象に残ったことは何ですか？",
    "最近、感謝していることはありますか？",
    "今日どんな挑戦がありましたか？どう対処しましたか？",
    "今一番やりたいことは何ですか？",
    "今日、誰と楽しい時間を過ごしましたか？",
    "今の状態を三つの言葉で表すと？",
    "今日、何か新しいことを学びましたか？",
    "もし今日をやり直せるなら、何を変えますか？",
    "最近、誇りに思ったことは何ですか？",
    "今日、思わず笑顔になった瞬間はありましたか？",
    "今、一番必要なものは何ですか？",
    "今日、予想外だったことはありますか？",
    "最近、心配していることはありますか？",
    "最後に心からリラックスしたのはいつですか？",
    "今、誰とでも話せるなら、誰を選びますか？",
    "今日、自分に優しくしたことは何ですか？",
]

DEFAULT_PROMPTS_MAP = {
    'zh-TW': DEFAULT_PROMPTS_ZH,
    'en': DEFAULT_PROMPTS_EN,
    'ja': DEFAULT_PROMPTS_JA,
}


class DailyPromptView(APIView):
    def get(self, request):
        today = timezone.now().date().isoformat()
        cache_key = f'daily_prompt_{request.user.id}_{today}'
        cached = cache.get(cache_key)
        if cached:
            return Response({'prompt': cached})

        # Generate prompt based on recent mood
        prompt_text = None
        try:
            recent = MoodNote.objects.filter(
                user=request.user,
                is_deleted=False,
                sentiment_score__isnull=False,
                created_at__gte=timezone.now() - timedelta(days=7),
            ).aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

            avg_s = recent['avg_s']
            avg_st = recent['avg_st']

            client = _get_openai_client()
            if client:
                lang = request.headers.get('Accept-Language', 'zh-TW')
                lang_map = {'zh-TW': 'Traditional Chinese', 'en': 'English', 'ja': 'Japanese'}
                lang_name = lang_map.get(lang, 'Traditional Chinese')
                mood_ctx = ''
                if avg_s is not None:
                    mood_ctx = f"The user's average mood score this week is {avg_s:.2f} (scale -1 to 1). "
                if avg_st is not None:
                    mood_ctx += f"Average stress level is {avg_st:.1f}/10. "

                resp = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{
                        'role': 'system',
                        'content': (
                            f'You are a gentle journaling coach. {mood_ctx}'
                            f'Generate one short, open-ended journaling prompt in {lang_name}. '
                            f'Keep it to ONE simple question (under 20 words). '
                            f'The prompt should be easy to start writing from directly. '
                            f'Avoid long instructions or multi-part questions. No quotes or labels.'
                        ),
                    }],
                    max_tokens=60,
                    temperature=0.8,
                    timeout=15,
                )
                prompt_text = resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning('Daily prompt generation failed: %s', e)

        if not prompt_text:
            lang = request.headers.get('Accept-Language', 'zh-TW')
            prompts = DEFAULT_PROMPTS_MAP.get(lang, DEFAULT_PROMPTS_ZH)
            prompt_text = random.choice(prompts)

        cache.set(cache_key, prompt_text, CACHE_TTL_DAILY_PROMPT)
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
