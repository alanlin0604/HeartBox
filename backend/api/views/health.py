"""Health metrics, sleep tracking, weekly summaries, habits, and reminders.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Avg
from django.http import FileResponse
from django.utils import timezone

from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    DailySleep, Habit, HabitLog, HealthMetric, MoodNote, ReminderSettings,
    WeeklySummary,
)
from ..serializers import (
    DailySleepSerializer, HabitLogSerializer, HabitSerializer,
    HealthMetricSerializer, HealthSyncSerializer, ReminderSettingsSerializer,
    WeeklySummarySerializer,
)
from ..services.pdf_export import generate_weekly_summary_pdf

from . import _get_openai_client, error_response, logger


class HealthMetricListView(generics.ListAPIView):
    """List health metrics for the authenticated user, filterable by type and date range."""
    serializer_class = HealthMetricSerializer

    def get_queryset(self):
        qs = HealthMetric.objects.filter(user=self.request.user)
        metric_type = self.request.query_params.get('type')
        if metric_type:
            qs = qs.filter(metric_type=metric_type)
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class HealthSyncView(APIView):
    """Batch upsert health metrics and sleep data from native health apps."""

    def post(self, request):
        serializer = HealthSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metrics_synced = 0
        sleep_synced = 0

        with transaction.atomic():
            # Upsert health metrics
            for metric_data in serializer.validated_data.get('metrics', []):
                HealthMetric.objects.update_or_create(
                    user=request.user,
                    date=metric_data['date'],
                    metric_type=metric_data['metric_type'],
                    defaults={
                        'value': metric_data['value'],
                        'source': metric_data.get('source', 'health_app'),
                    },
                )
                metrics_synced += 1

            # Upsert sleep data
            for sleep_data in serializer.validated_data.get('sleep', []):
                defaults = {
                    'sleep_hours': sleep_data['sleep_hours'],
                    'sleep_quality': sleep_data['sleep_quality'],
                    'source': sleep_data.get('source', 'health_app'),
                }
                for field in ('bedtime', 'wake_time', 'deep_sleep_minutes',
                              'light_sleep_minutes', 'rem_sleep_minutes'):
                    if field in sleep_data and sleep_data[field] is not None:
                        defaults[field] = sleep_data[field]

                DailySleep.objects.update_or_create(
                    user=request.user,
                    date=sleep_data['date'],
                    defaults=defaults,
                )
                sleep_synced += 1

        return Response({
            'metrics_synced': metrics_synced,
            'sleep_synced': sleep_synced,
        }, status=status.HTTP_200_OK)


class HealthSummaryView(APIView):
    """Get a summary of recent health data for dashboard display."""

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        cutoff = timezone.localdate() - timedelta(days=days)
        user = request.user

        metrics = HealthMetric.objects.filter(user=user, date__gte=cutoff)

        # Aggregate by metric type
        summary = {}
        for metric_type, label in HealthMetric.METRIC_CHOICES:
            type_metrics = metrics.filter(metric_type=metric_type).order_by('date')
            if type_metrics.exists():
                agg = type_metrics.aggregate(
                    avg=Avg('value'),
                )
                summary[metric_type] = {
                    'avg': round(agg['avg'], 1) if agg['avg'] else None,
                    'latest': type_metrics.last().value if type_metrics.exists() else None,
                    'trend': list(type_metrics.values('date', 'value')),
                }

        # Sleep summary
        sleep_records = DailySleep.objects.filter(user=user, date__gte=cutoff).order_by('date')
        if sleep_records.exists():
            sleep_agg = sleep_records.aggregate(
                avg_hours=Avg('sleep_hours'),
                avg_quality=Avg('sleep_quality'),
            )
            summary['sleep'] = {
                'avg_hours': round(sleep_agg['avg_hours'], 1) if sleep_agg['avg_hours'] else None,
                'avg_quality': round(sleep_agg['avg_quality'], 1) if sleep_agg['avg_quality'] else None,
                'trend': list(sleep_records.values(
                    'date', 'sleep_hours', 'sleep_quality',
                    'deep_sleep_minutes', 'light_sleep_minutes', 'rem_sleep_minutes',
                )),
            }

        # Health-mood correlation: average sentiment on days with health data
        from ..services.analytics import get_health_mood_correlation
        health_mood = get_health_mood_correlation(user, days)

        return Response({
            'summary': summary,
            'health_mood_correlation': health_mood,
        })


class ReminderSettingsView(APIView):
    """Get or update user's daily reminder settings."""

    def get(self, request):
        settings, created = ReminderSettings.objects.get_or_create(user=request.user)
        serializer = ReminderSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        settings, created = ReminderSettings.objects.get_or_create(user=request.user)
        serializer = ReminderSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DailySleepView(APIView):
    """GET today's sleep record, POST/PUT to upsert."""

    def get(self, request):
        date_str = request.query_params.get('date')
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return error_response('invalid_date_format', 'Invalid date format. Use YYYY-MM-DD.')
        else:
            date = timezone.localdate()
        try:
            record = DailySleep.objects.get(user=request.user, date=date)
            return Response(DailySleepSerializer(record).data)
        except DailySleep.DoesNotExist:
            return Response({'date': str(date), 'sleep_hours': None, 'sleep_quality': None})

    def post(self, request):
        date = request.data.get('date', str(timezone.localdate()))
        record, _created = DailySleep.objects.update_or_create(
            user=request.user,
            date=date,
            defaults={
                'sleep_hours': request.data.get('sleep_hours'),
                'sleep_quality': request.data.get('sleep_quality'),
            },
        )
        # Trigger achievement check (first_sleep_log / sleep_streak_7 / quality_sleeper)
        try:
            from ..services.achievements import check_achievements
            check_achievements(request.user)
        except Exception:
            pass
        return Response(DailySleepSerializer(record).data, status=status.HTTP_200_OK)


class DailySleepListView(generics.ListAPIView):
    serializer_class = DailySleepSerializer

    def get_queryset(self):
        return DailySleep.objects.filter(user=self.request.user)


class SleepAnalysisView(APIView):
    """綜合睡眠分析 - 統計、情緒關聯、壓力關聯、問題識別、建議"""

    def get(self, request):
        from ..services.sleep_analysis import (
            analyze_sleep_mood_correlation,
            analyze_sleep_stress_correlation,
            get_sleep_statistics,
            identify_sleep_issues,
            generate_sleep_recommendations,
        )

        days = int(request.query_params.get('days', 30))

        # 獲取各項分析結果
        statistics = get_sleep_statistics(request.user, days)
        mood_correlation = analyze_sleep_mood_correlation(request.user, days)
        stress_correlation = analyze_sleep_stress_correlation(request.user, days)
        issues_data = identify_sleep_issues(request.user, days=min(days, 14))
        recommendations = generate_sleep_recommendations(request.user, days=min(days, 14))

        return Response({
            'statistics': statistics,
            'mood_correlation': mood_correlation,
            'stress_correlation': stress_correlation,
            'issues': issues_data.get('issues', []),
            'recommendations': recommendations
        })


class SleepCalendarView(APIView):
    """睡眠日曆 - 每日睡眠記錄 + quality_score + pattern"""

    def get(self, request):
        from ..serializers import DailySleepDetailSerializer

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return error_response('missing_params', 'start_date and end_date are required')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return error_response('invalid_date_format', 'Invalid date format. Use YYYY-MM-DD.')

        if end_date < start_date:
            return error_response('invalid_range', 'end_date must be >= start_date')

        sleeps = DailySleep.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        calendar_data = DailySleepDetailSerializer(sleeps, many=True).data

        return Response({
            'calendar': calendar_data
        })


class SleepTrendsView(APIView):
    """睡眠趨勢 - 週度聚合資料"""

    def get(self, request):
        days = int(request.query_params.get('days', 90))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # 獲取睡眠記錄
        sleeps = DailySleep.objects.filter(
            user=request.user,
            date__gte=start_date
        ).order_by('date')

        # 獲取情緒記錄（用於關聯）
        mood_notes = MoodNote.objects.filter(
            user=request.user,
            created_at__date__gte=start_date,
            sentiment_score__isnull=False,
            is_deleted=False
        ).values('created_at__date', 'sentiment_score')

        # 計算每日平均情緒
        mood_by_date = {}
        for note in mood_notes:
            date = note['created_at__date']
            score = note['sentiment_score']
            if date not in mood_by_date:
                mood_by_date[date] = []
            mood_by_date[date].append((score + 1) * 5)  # 轉換為 0-10

        # 按週聚合
        from collections import defaultdict
        weeks = defaultdict(lambda: {'sleep_hours': [], 'quality_scores': [], 'moods': []})

        for sleep in sleeps:
            # 計算該日期屬於哪一週（ISO week）
            week_start = sleep.date - timedelta(days=sleep.date.weekday())

            weeks[week_start]['sleep_hours'].append(sleep.sleep_hours)

            # 計算品質分數
            from ..services.sleep_analysis import calculate_quality_score
            score = calculate_quality_score(
                sleep.sleep_hours,
                sleep.deep_sleep_minutes,
                sleep.light_sleep_minutes,
                sleep.rem_sleep_minutes
            )
            weeks[week_start]['quality_scores'].append(score)

            # 加入情緒資料
            if sleep.date in mood_by_date:
                avg_mood = sum(mood_by_date[sleep.date]) / len(mood_by_date[sleep.date])
                weeks[week_start]['moods'].append(avg_mood)

        # 生成趨勢資料
        trends = []
        for week_start in sorted(weeks.keys()):
            data = weeks[week_start]
            trends.append({
                'week_start': str(week_start),
                'avg_sleep_hours': round(sum(data['sleep_hours']) / len(data['sleep_hours']), 1) if data['sleep_hours'] else None,
                'avg_quality_score': round(sum(data['quality_scores']) / len(data['quality_scores'])) if data['quality_scores'] else None,
                'avg_mood': round(sum(data['moods']) / len(data['moods']), 1) if data['moods'] else None
            })

        return Response({
            'trends': trends
        })


class SleepInsightsView(APIView):
    """睡眠洞察 - 有趣的統計發現"""

    def get(self, request):
        from ..services.sleep_analysis import calculate_quality_score

        insights = []
        user = request.user
        end_date = timezone.now().date()

        # 取得最近 90 天的睡眠記錄
        sleeps = DailySleep.objects.filter(
            user=user,
            date__gte=end_date - timedelta(days=90)
        ).order_by('-date')

        if sleeps.count() < 7:
            return Response({'insights': ['資料不足，至少需要 7 天的睡眠記錄']})

        # 洞察 1: 週末 vs 平日睡眠差異
        weekday_hours = []
        weekend_hours = []

        for sleep in sleeps:
            weekday = sleep.date.weekday()  # 0=Monday, 6=Sunday
            if weekday < 5:  # 平日
                weekday_hours.append(sleep.sleep_hours)
            else:  # 週末
                weekend_hours.append(sleep.sleep_hours)

        if weekday_hours and weekend_hours:
            avg_weekday = sum(weekday_hours) / len(weekday_hours)
            avg_weekend = sum(weekend_hours) / len(weekend_hours)
            diff = avg_weekend - avg_weekday

            if abs(diff) > 0.5:
                if diff > 0:
                    insights.append(f'週末平均多睡 {diff:.1f} 小時（可能平日睡眠不足）')
                else:
                    insights.append(f'週末平均少睡 {abs(diff):.1f} 小時（作息相當規律）')

        # 洞察 2: 最佳睡眠時數（情緒最好的睡眠時數）
        mood_notes = MoodNote.objects.filter(
            user=user,
            created_at__date__gte=end_date - timedelta(days=90),
            sentiment_score__isnull=False,
            is_deleted=False
        ).values('created_at__date', 'sentiment_score')

        mood_by_date = {}
        for note in mood_notes:
            date = note['created_at__date']
            score = (note['sentiment_score'] + 1) * 5  # 轉換為 0-10
            if date not in mood_by_date:
                mood_by_date[date] = []
            mood_by_date[date].append(score)

        # 按睡眠時數分組（6-7h, 7-8h, 8-9h, 9+h）
        from collections import defaultdict
        mood_by_hours = defaultdict(list)

        for sleep in sleeps:
            if sleep.date in mood_by_date:
                avg_mood = sum(mood_by_date[sleep.date]) / len(mood_by_date[sleep.date])
                if 6 <= sleep.sleep_hours < 7:
                    mood_by_hours['6-7h'].append(avg_mood)
                elif 7 <= sleep.sleep_hours < 8:
                    mood_by_hours['7-8h'].append(avg_mood)
                elif 8 <= sleep.sleep_hours < 9:
                    mood_by_hours['8-9h'].append(avg_mood)
                elif sleep.sleep_hours >= 9:
                    mood_by_hours['9+h'].append(avg_mood)

        # 找出情緒最好的睡眠時數區間
        best_range = None
        best_mood = 0
        for hours_range, moods in mood_by_hours.items():
            if len(moods) >= 3:  # 至少 3 個樣本
                avg = sum(moods) / len(moods)
                if avg > best_mood:
                    best_mood = avg
                    best_range = hours_range

        if best_range:
            insights.append(f'您在睡眠 {best_range} 時情緒最佳（平均 {best_mood:.1f}/10）')

        # 洞察 3: 連續最佳睡眠記錄
        best_streak = 0
        current_streak = 0

        for sleep in reversed(list(sleeps)):
            score = calculate_quality_score(
                sleep.sleep_hours,
                sleep.deep_sleep_minutes,
                sleep.light_sleep_minutes,
                sleep.rem_sleep_minutes
            )
            if score >= 80:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0

        if best_streak >= 3:
            insights.append(f'最長連續優質睡眠記錄：{best_streak} 天')

        # 洞察 4: 深度睡眠與品質的關係
        deep_sleep_records = [s for s in sleeps if s.deep_sleep_minutes is not None and s.deep_sleep_minutes > 0]
        if len(deep_sleep_records) >= 10:
            total_minutes = sum([s.deep_sleep_minutes + s.light_sleep_minutes + s.rem_sleep_minutes
                                for s in deep_sleep_records
                                if s.light_sleep_minutes and s.rem_sleep_minutes])
            total_deep = sum([s.deep_sleep_minutes for s in deep_sleep_records])

            if total_minutes > 0:
                avg_deep_pct = (total_deep / total_minutes) * 100
                insights.append(f'平均深度睡眠佔比 {avg_deep_pct:.1f}%（建議 20-25%）')

        if not insights:
            insights.append('繼續記錄睡眠數據，我們將為您提供更多洞察')

        return Response({
            'insights': insights
        })


class WeeklySummaryView(APIView):
    def _is_pdf_request(self, request):
        """Check if PDF export requested (supports both 'export' and 'format' params)."""
        return request.query_params.get('export') == 'pdf' or request.query_params.get('format') == 'pdf'

    def _generate_pdf_response(self, summary, request):
        """Generate and return a PDF FileResponse for the given summary."""
        week_end = summary.week_start + timedelta(days=6)
        notes_qs = MoodNote.objects.filter(
            user=request.user,
            is_deleted=False,
            created_at__date__gte=summary.week_start,
            created_at__date__lte=week_end,
        ).order_by('created_at')
        lang = request.query_params.get('lang') or request.headers.get('Accept-Language', 'zh-TW').split(',')[0].strip()
        buf = generate_weekly_summary_pdf(summary, notes_qs, request.user, lang=lang)
        filename = f'weekly_summary_{summary.week_start}.pdf'
        return FileResponse(buf, as_attachment=True, filename=filename, content_type='application/pdf')

    def get(self, request):
        # Support PDF export by summary ID (for cached old frontend versions)
        summary_id = request.query_params.get('id')
        if summary_id and self._is_pdf_request(request):
            try:
                # Try with user filter first, then without (in case of user mismatch)
                summary = WeeklySummary.objects.filter(id=summary_id, user=request.user).first()
                if not summary:
                    # Log for debugging
                    exists = WeeklySummary.objects.filter(id=summary_id).exists()
                    logger.warning('Weekly PDF by ID=%s: user=%s, exists_any_user=%s', summary_id, request.user.id, exists)
                    return error_response('summary_not_found', 'Summary not found.', 404)
                return self._generate_pdf_response(summary, request)
            except Exception as e:
                logger.error('Weekly summary PDF (id=%s) failed: %s', summary_id, e, exc_info=True)
                return error_response('pdf_failed', 'PDF generation failed.', 500)

        week_start_str = request.query_params.get('week_start')
        if not week_start_str:
            return error_response('week_start_required', 'week_start parameter required (YYYY-MM-DD).')
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            return error_response('invalid_date_format', 'Invalid date format.')

        # Auto-adjust to Monday of the given week
        weekday = week_start.weekday()  # 0=Monday, 6=Sunday
        if weekday != 0:
            week_start = week_start - timedelta(days=weekday)

        # Try to find existing
        summary = WeeklySummary.objects.filter(user=request.user, week_start=week_start).first()

        if summary:
            # Always refresh note_count to reflect current actual count
            week_end = week_start + timedelta(days=6)
            actual_count = MoodNote.objects.filter(
                user=request.user, is_deleted=False,
                created_at__date__gte=week_start, created_at__date__lte=week_end,
            ).count()
            if summary.note_count != actual_count:
                summary.note_count = actual_count
                summary.save(update_fields=['note_count'])

        if not summary:
            # Generate new summary
            week_end = week_start + timedelta(days=6)
            notes = MoodNote.objects.filter(
                user=request.user,
                is_deleted=False,
                created_at__date__gte=week_start,
                created_at__date__lte=week_end,
            )
            note_count = notes.count()
            if note_count == 0:
                return error_response('no_notes_this_week', 'No notes found for this week.', 404)

            agg = notes.aggregate(avg_s=Avg('sentiment_score'), avg_st=Avg('stress_index'))

            # Count activities
            activity_counts = {}
            for note in notes.values('metadata'):
                meta = note.get('metadata') or {}
                for act in meta.get('activities', []):
                    activity_counts[act] = activity_counts.get(act, 0) + 1
            top_activities = sorted(
                [{'name': k, 'count': v} for k, v in activity_counts.items()],
                key=lambda x: x['count'], reverse=True,
            )[:5]

            # Generate AI summary
            ai_summary = ''
            try:
                client = _get_openai_client()
                if client:
                    lang = request.headers.get('Accept-Language', 'zh-TW')
                    lang_map = {'zh-TW': 'Traditional Chinese', 'en': 'English', 'ja': 'Japanese'}
                    lang_name = lang_map.get(lang, 'Traditional Chinese')

                    # Collect diary content snippets (use search_text to avoid decryption overhead)
                    note_previews = list(notes.values_list('search_text', flat=True))
                    diary_snippets = '\n---\n'.join(
                        [(t[:200] if t else '') for t in note_previews if t]
                    )

                    content = (
                        f'You are a warm, professional mental health assistant. '
                        f'Generate a weekly mental health summary in {lang_name} based on the following data:\n\n'
                        f'Period: {week_start} to {week_end}\n'
                        f'Journal entries: {note_count}\n'
                        f'Average mood: {agg["avg_s"]:.2f} (-1 to 1 scale)\n'
                        f'Average stress: {agg["avg_st"]:.1f} (0-10 scale)\n'
                        f'Top activities: {top_activities}\n\n'
                        f'--- Diary excerpts ---\n{diary_snippets}\n\n'
                        f'Based on ALL the above data (diary content, mood, stress, activities), '
                        f'provide a comprehensive analysis with:\n'
                        f'1. Key emotional themes and patterns observed this week\n'
                        f'2. Specific observations tied to diary content\n'
                        f'3. Personalized suggestions based on what the user wrote\n'
                        f'Be warm, supportive, and specific (not generic).'
                    )

                    # Dynamic token limit: base 300 + 100 per diary entry, cap at 1500
                    max_tok = min(300 + note_count * 100, 1500)

                    resp = client.chat.completions.create(
                        model='gpt-4o-mini',
                        messages=[{'role': 'system', 'content': content}],
                        max_tokens=max_tok,
                        temperature=0.7,
                        timeout=30,
                    )
                    ai_summary = resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning('Weekly summary AI generation failed: %s', e)

            summary = WeeklySummary.objects.create(
                user=request.user,
                week_start=week_start,
                mood_avg=round(agg['avg_s'], 2) if agg['avg_s'] is not None else None,
                stress_avg=round(agg['avg_st'], 1) if agg['avg_st'] is not None else None,
                note_count=note_count,
                top_activities=top_activities,
                ai_summary=ai_summary,
            )

        # Check if PDF export requested
        if self._is_pdf_request(request):
            try:
                return self._generate_pdf_response(summary, request)
            except Exception as e:
                logger.error('Weekly summary PDF generation failed: %s', e, exc_info=True)
                return error_response('pdf_failed', 'PDF generation failed.', 500)

        return Response(WeeklySummarySerializer(summary).data)


class WeeklySummaryListView(generics.ListAPIView):
    serializer_class = WeeklySummarySerializer

    def get_queryset(self):
        return WeeklySummary.objects.filter(user=self.request.user)


class HabitViewSet(viewsets.ModelViewSet):
    """Habit CRUD operations."""
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Habit.objects.none()
        # Prefetch the last 365 days of logs so the serializer can compute
        # streak / completion_rate / checked_today in Python without firing
        # ~62 queries per habit (see audit 2026-05-15).
        from django.db.models import Prefetch
        cutoff = timezone.now().date() - timedelta(days=365)
        return (
            Habit.objects.filter(user=self.request.user)
            .prefetch_related(
                Prefetch(
                    'logs',
                    queryset=HabitLog.objects.filter(date__gte=cutoff).only('id', 'habit_id', 'date'),
                    to_attr='_recent_logs',
                )
            )
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def check_in(self, request, pk=None):
        """POST: check in for today (idempotent — re-checking is a no-op).
        DELETE: undo today's check-in."""
        habit = self.get_object()
        today = timezone.now().date()

        if request.method == 'DELETE':
            removed = HabitLog.objects.filter(habit=habit, date=today).delete()[0]
            return Response({'removed': removed})

        existing = HabitLog.objects.filter(habit=habit, date=today).first()
        if existing:
            # Idempotent: caller is allowed to update the note even if already checked in.
            new_note = request.data.get('note')
            if new_note is not None and new_note != existing.note:
                existing.note = new_note
                existing.save(update_fields=['note'])
            return Response(HabitLogSerializer(existing).data)

        log = HabitLog.objects.create(
            habit=habit,
            user=request.user,
            date=today,
            note=request.data.get('note', '') or '',
        )
        # Trigger achievement check (habit_streak_7 / habit_streak_30 / first_habit)
        try:
            from ..services.achievements import check_achievements
            check_achievements(request.user)
        except Exception:
            pass
        return Response(HabitLogSerializer(log).data, status=201)

    @action(detail=True, methods=['get'])
    def calendar(self, request, pk=None):
        """Get habit check-in calendar (last 90 days)."""
        habit = self.get_object()

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)

        logs = HabitLog.objects.filter(
            habit=habit,
            date__gte=start_date,
            date__lte=end_date
        ).values('date')

        # Convert to date list
        completed_dates = [log['date'].isoformat() for log in logs]

        return Response({
            'habit_id': habit.id,
            'completed_dates': completed_dates,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
        })


class HabitAnalyticsView(APIView):
    """Habit and mood correlation analysis.

    Pulls all habits + all habit logs + all mood notes for the user in the
    last 30 days in 3 queries (was N+1: 1 habits + 3*habits queries — for
    10 habits that was 31 queries). Then groups in Python.

    Response shape matches what HabitCorrelation.jsx reads:
        {"analytics": [
            {"habit_id", "habit_name",
             "avg_mood_completed", "avg_mood_not_completed",
             "mood_difference", "days_completed"},
            ...
        ]}
    Field names and the {analytics: ...} envelope are required for the
    chart to render — earlier shape was a bare list with `_when_` infix
    field names, which silently rendered as an empty chart.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        habits = list(Habit.objects.filter(user=request.user, is_active=True))
        habit_ids = [h.id for h in habits]

        # All check-ins in window, in one query.
        log_rows = HabitLog.objects.filter(
            habit_id__in=habit_ids,
            date__gte=start_date,
            date__lte=end_date,
        ).values_list('habit_id', 'date')
        completed_by_habit = {hid: set() for hid in habit_ids}
        all_completed_dates = set()
        for hid, d in log_rows:
            completed_by_habit[hid].add(d)
            all_completed_dates.add(d)

        # All mood notes in window, in one query — keyed by date.
        note_rows = MoodNote.objects.filter(
            user=request.user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            sentiment_score__isnull=False,
        ).values_list('created_at__date', 'sentiment_score')
        sentiment_by_date = {}
        for d, score in note_rows:
            sentiment_by_date.setdefault(d, []).append(score)

        def avg(scores):
            return sum(scores) / len(scores) if scores else 0

        results = []
        for habit in habits:
            completed_dates = completed_by_habit[habit.id]
            if not completed_dates:
                continue
            completed_scores = []
            uncompleted_scores = []
            for d, scores in sentiment_by_date.items():
                bucket = completed_scores if d in completed_dates else uncompleted_scores
                bucket.extend(scores)
            avg_completed = avg(completed_scores)
            avg_not_completed = avg(uncompleted_scores)
            results.append({
                'habit_id': habit.id,
                'habit_name': habit.name,
                'avg_mood_completed': round(avg_completed, 2),
                'avg_mood_not_completed': round(avg_not_completed, 2),
                'mood_difference': round(avg_completed - avg_not_completed, 2),
                'days_completed': len(completed_dates),
            })

        results.sort(key=lambda x: abs(x['mood_difference']), reverse=True)
        return Response({'analytics': results})
