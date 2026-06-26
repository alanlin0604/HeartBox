import logging
import math
import zoneinfo
from datetime import timedelta

import numpy as np
import pandas as pd
from django.db.models import Avg
from django.utils import timezone
from scipy import stats

logger = logging.getLogger(__name__)


def _user_now(user_timezone='Asia/Taipei'):
    """Return current datetime in user's timezone."""
    try:
        tz = zoneinfo.ZoneInfo(user_timezone)
    except (KeyError, Exception):
        tz = zoneinfo.ZoneInfo('Asia/Taipei')
    return timezone.now().astimezone(tz)


def get_recommended_counselors(user):
    """Get counselor IDs recommended based on user's frequent tags vs counselor specialty."""
    from api.models import MoodNote
    from django.contrib.auth import get_user_model

    User = get_user_model()

    # Get user's top tags
    notes = MoodNote.objects.filter(user=user, is_deleted=False)
    tag_counts = {}
    for meta in notes.values_list('metadata', flat=True)[:200]:
        for tag in (meta or {}).get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:5]
    if not top_tags:
        return []

    from django.db.models import Q
    q = Q()
    for tag in top_tags:
        q |= Q(counselor_profile__specialty__icontains=tag)

    return list(
        User.objects.filter(q, counselor_profile__status='approved')
        .values_list('id', flat=True)
        .distinct()[:10]
    )


def _sanitize(obj):
    """Recursively replace NaN/Inf float values with None for JSON safety."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (np.floating, np.integer)):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def get_mood_trends(queryset, period='week', lookback_days=30):
    """Calculate mood trends over time. Returns Recharts-compatible LineChart data."""
    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(
        created_at__gte=since,
        sentiment_score__isnull=False,
    ).values('created_at', 'sentiment_score', 'stress_index')

    if not notes:
        return []

    df = pd.DataFrame(list(notes))
    df['date'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)

    if period == 'week':
        # User-friendly label: the Monday of that ISO week as ``M/D``
        # (e.g. ``2/9`` instead of ``2026-W07``). Year added only when the
        # range crosses a year boundary so the axis stays readable.
        # ``sort_key`` keeps ISO ``YYYY-Www`` for stable ordering.
        iso = df['date'].dt.isocalendar()
        df['sort_key'] = iso.year.astype(str) + '-W' + iso.week.astype(str).str.zfill(2)
        # Monday of the same ISO week (weekday=0). dt.weekday: Mon=0..Sun=6
        monday = df['date'] - pd.to_timedelta(df['date'].dt.weekday, unit='D')
        spans_years = monday.dt.year.nunique() > 1
        if spans_years:
            df['period'] = monday.dt.strftime('%Y/%m/%d')
        else:
            df['period'] = monday.dt.strftime('%m/%d')
    else:  # month
        # Same idea — ``M月`` (zh) translates poorly across locales, so
        # keep the numeric ``YYYY/MM`` form (everyone reads dates this way).
        spans_years = df['date'].dt.year.nunique() > 1
        if spans_years:
            df['period'] = df['date'].dt.strftime('%Y/%m')
        else:
            df['period'] = df['date'].dt.strftime('%m')
        df['sort_key'] = df['date'].dt.to_period('M').astype(str)

    grouped = df.groupby(['period', 'sort_key']).agg(
        avg_sentiment=('sentiment_score', 'mean'),
        avg_stress=('stress_index', 'mean'),
        count=('sentiment_score', 'count'),
    ).reset_index()
    # Sort by the ISO key so the line chart reads left-to-right
    # chronologically even when string labels wouldn't naturally sort
    # that way (e.g. '12/29' < '01/05' lexically).
    grouped = grouped.sort_values('sort_key').drop(columns=['sort_key'])

    grouped['avg_sentiment'] = grouped['avg_sentiment'].round(2)
    grouped['avg_stress'] = grouped['avg_stress'].round(1)

    return _sanitize(grouped.rename(columns={'period': 'name'}).to_dict(orient='records'))


def get_mood_weather_correlation(queryset, lookback_days=90):
    """Mood vs temperature analytics.

    Returns three views of the same paired data so the frontend can pick the
    most informative shape:
      * ``scatter_data``: raw (temperature, sentiment) pairs for the
        original scatter plot
      * ``mood_by_temperature``: BAR-CHART-READY buckets — temperature is
        cut into climate-meaningful ranges (``<15``, ``15-20``, ``20-25``,
        ``25-30``, ``>=30`` deg C) and we report avg sentiment + count per
        bucket. This is what the dashboard renders; the scatter is kept
        for power users and inspection.
      * ``best_temp_bucket``: the bucket with the highest avg sentiment,
        ready for a "你在 20-25°C 時心情最好" headline.
      * ``correlation`` / ``p_value`` / ``sample_size``: kept for the
        Pearson r line under the chart.
    """
    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(
        created_at__gte=since,
        sentiment_score__isnull=False,
    ).values('sentiment_score', 'metadata')

    pairs = []
    for note in notes:
        meta = note.get('metadata') or {}
        temp = meta.get('temperature')
        if temp is not None:
            try:
                pairs.append({
                    'sentiment': note['sentiment_score'],
                    'temperature': float(temp),
                })
            except (ValueError, TypeError):
                continue

    if len(pairs) < 3:
        return {
            'correlation': None, 'p_value': None,
            'scatter_data': pairs, 'mood_by_temperature': [],
            'best_temp_bucket': None, 'sample_size': len(pairs),
        }

    df = pd.DataFrame(pairs)
    try:
        r, p = stats.pearsonr(df['sentiment'], df['temperature'])
    except Exception:
        r, p = None, None

    # Climate-meaningful temperature buckets. Edges chosen for TW context.
    bucket_edges = [(-100.0, 15.0), (15.0, 20.0), (20.0, 25.0), (25.0, 30.0), (30.0, 100.0)]
    bucket_labels = ['<15', '15-20', '20-25', '25-30', '>=30']
    buckets = []
    for (lo, hi), label in zip(bucket_edges, bucket_labels):
        subset = df[(df['temperature'] >= lo) & (df['temperature'] < hi)]
        if len(subset) == 0:
            continue
        buckets.append({
            'bucket': label,
            'avg_sentiment': round(float(subset['sentiment'].mean()), 3),
            'count': int(len(subset)),
            # The center is kept for ordering when the frontend sorts; the
            # default order is already low-to-high so the chart reads
            # left-to-right cold-to-warm.
            'center': (lo + hi) / 2.0,
        })

    # Best bucket: the temperature range where the user's mood was highest.
    # Restricted to buckets with at least 2 observations so a one-shot
    # outlier doesn't get crowned "best."
    eligible = [b for b in buckets if b['count'] >= 2]
    best_temp_bucket = (
        max(eligible, key=lambda b: b['avg_sentiment'])
        if eligible else None
    )

    return _sanitize({
        'correlation': round(r, 3) if r is not None else None,
        'p_value': round(p, 4) if p is not None else None,
        'scatter_data': pairs,
        'mood_by_temperature': buckets,
        'best_temp_bucket': best_temp_bucket,
        'sample_size': len(pairs),
    })


def get_calendar_data(queryset, year, month):
    """Return per-day average sentiment and note count for a given month."""
    notes = queryset.filter(
        created_at__year=year,
        created_at__month=month,
        sentiment_score__isnull=False,
    ).values('created_at', 'sentiment_score')

    if not notes:
        return []

    df = pd.DataFrame(list(notes))
    df['date'] = pd.to_datetime(df['created_at']).dt.date

    grouped = df.groupby('date').agg(
        avg_sentiment=('sentiment_score', 'mean'),
        count=('sentiment_score', 'count'),
    ).reset_index()

    grouped['avg_sentiment'] = grouped['avg_sentiment'].round(2)
    grouped['date'] = grouped['date'].astype(str)

    return _sanitize(grouped.to_dict(orient='records'))


def get_frequent_tags(queryset, lookback_days=90, top_n=10):
    """Aggregate tag frequency from Tag model and legacy metadata.tags. Returns Recharts BarChart data."""
    from django.db.models import Count

    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(created_at__gte=since)

    tag_counts = {}

    # Get counts from new Tag model (many-to-many)
    from ..models import Tag
    user = notes.first().user if notes.exists() else None
    if user:
        tag_data = Tag.objects.filter(
            user=user,
            notes__in=notes,
            notes__is_deleted=False
        ).annotate(count=Count('notes')).values('name', 'count')

        for tag in tag_data:
            tag_counts[tag['name']] = tag_counts.get(tag['name'], 0) + tag['count']

    # Also get counts from legacy metadata.tags for backward compatibility
    for meta in notes.values_list('metadata', flat=True):
        tags = (meta or {}).get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{'name': tag, 'count': count} for tag, count in sorted_tags]


def get_stress_by_tag(queryset, lookback_days=90):
    """Average stress index per tag for RadarChart. Returns [{tag, avg_stress, count}]."""
    from django.db.models import Avg, Count
    from ..models import Tag

    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(
        created_at__gte=since,
        stress_index__isnull=False,
    )

    tag_stress = {}  # tag -> [stress_values]

    # Get stress data from new Tag model
    user = notes.first().user if notes.exists() else None
    if user:
        tag_data = Tag.objects.filter(
            user=user,
            notes__in=notes,
            notes__is_deleted=False,
            notes__stress_index__isnull=False
        ).annotate(
            avg_stress=Avg('notes__stress_index'),
            count=Count('notes')
        ).values('name', 'avg_stress', 'count')

        for tag in tag_data:
            if tag['name'] not in tag_stress:
                tag_stress[tag['name']] = []
            # Approximate stress values from average (for combining with legacy data)
            tag_stress[tag['name']].extend([tag['avg_stress']] * tag['count'])

    # Also get stress data from legacy metadata.tags
    for note in notes.values('stress_index', 'metadata'):
        meta = note.get('metadata') or {}
        tags = meta.get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                tag_stress.setdefault(tag, []).append(note['stress_index'])

    result = []
    for tag, values in tag_stress.items():
        result.append({
            'tag': tag,
            'avg_stress': round(sum(values) / len(values), 1),
            'count': len(values),
        })

    result.sort(key=lambda x: x['count'], reverse=True)
    return result[:10]


def get_activity_mood_correlation(queryset, lookback_days=90):
    """Stats per activity: avg sentiment and count. Returns [{name, avg_sentiment, count}]."""
    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(
        created_at__gte=since,
        sentiment_score__isnull=False,
    ).values('sentiment_score', 'metadata')

    activity_data = {}  # activity_name -> [sentiment_values]
    for note in notes:
        meta = note.get('metadata') or {}
        activities = meta.get('activities', [])
        if isinstance(activities, list):
            for act in activities:
                activity_data.setdefault(act, []).append(note['sentiment_score'])

    result = []
    for name, values in activity_data.items():
        result.append({
            'name': name,
            'avg_sentiment': round(sum(values) / len(values), 2),
            'count': len(values),
        })
    result.sort(key=lambda x: x['count'], reverse=True)
    return result


def get_sleep_mood_correlation(queryset, lookback_days=90):
    """Pearson correlation between sleep hours/quality and sentiment.

    Reads from DailySleep model (primary) and falls back to legacy
    note metadata for older data.
    """
    from ..models import DailySleep

    since = timezone.now() - timedelta(days=lookback_days)
    user = queryset.first()
    user_obj = user.user if user else None

    pairs = []

    # Primary source: DailySleep records joined with daily avg sentiment
    if user_obj:
        sleep_records = DailySleep.objects.filter(
            user=user_obj, date__gte=since.date(),
        ).values('date', 'sleep_hours', 'sleep_quality')

        for rec in sleep_records:
            day_notes = queryset.filter(
                created_at__date=rec['date'],
                sentiment_score__isnull=False,
            )
            avg = day_notes.aggregate(avg=Avg('sentiment_score'))['avg']
            if avg is not None:
                pairs.append({
                    'sentiment': round(avg, 3),
                    'sleep_hours': float(rec['sleep_hours']),
                    'sleep_quality': rec['sleep_quality'],
                })
        seen_dates = {r['date'] for r in sleep_records}
    else:
        seen_dates = set()

    # Fallback: legacy note metadata (for older data before DailySleep model)
    notes = queryset.filter(
        created_at__gte=since,
        sentiment_score__isnull=False,
    ).values('sentiment_score', 'metadata', 'created_at')

    for note in notes:
        note_date = note['created_at'].date() if hasattr(note['created_at'], 'date') else note['created_at']
        if note_date in seen_dates:
            continue
        meta = note.get('metadata') or {}
        sleep_hours = meta.get('sleep_hours')
        if sleep_hours is not None:
            try:
                pairs.append({
                    'sentiment': note['sentiment_score'],
                    'sleep_hours': float(sleep_hours),
                    'sleep_quality': int(meta['sleep_quality']) if meta.get('sleep_quality') is not None else None,
                })
            except (ValueError, TypeError):
                continue

    if len(pairs) < 3:
        return {'hours_correlation': None, 'scatter_data': pairs, 'sample_size': len(pairs)}

    df = pd.DataFrame(pairs)
    result = {'scatter_data': pairs, 'sample_size': len(pairs)}
    try:
        r, p = stats.pearsonr(df['sentiment'], df['sleep_hours'])
        result['hours_correlation'] = round(r, 3)
        result['hours_p_value'] = round(p, 4)
    except Exception:
        result['hours_correlation'] = None

    quality_pairs = df.dropna(subset=['sleep_quality'])
    if len(quality_pairs) >= 3:
        try:
            r, p = stats.pearsonr(quality_pairs['sentiment'], quality_pairs['sleep_quality'])
            result['quality_correlation'] = round(r, 3)
            result['quality_p_value'] = round(p, 4)
        except Exception:
            result['quality_correlation'] = None
    return _sanitize(result)


def get_gratitude_stats(queryset):
    """Count gratitude notes and calculate consecutive gratitude days streak."""
    gratitude_notes = queryset.filter(metadata__type='gratitude')
    gratitude_count = gratitude_notes.count()

    # Calculate gratitude streak
    gratitude_streak = 0
    if gratitude_count > 0:
        dates = list(
            gratitude_notes.values_list('created_at__date', flat=True)
            .distinct()
            .order_by('-created_at__date')[:366]
        )
        if dates:
            today = timezone.localdate()
            streak = 0
            expected = today
            for d in dates:
                if d == expected:
                    streak += 1
                    expected = d - timedelta(days=1)
                elif d == today - timedelta(days=1) and streak == 0:
                    streak = 1
                    expected = d - timedelta(days=1)
                else:
                    break
            gratitude_streak = streak

    return {
        'gratitude_count': gratitude_count,
        'gratitude_streak': gratitude_streak,
    }


def get_year_pixels(queryset, year):
    """Per-day average sentiment for the entire year. Returns {date_str: avg_sentiment}."""
    notes = queryset.filter(
        created_at__year=year,
        sentiment_score__isnull=False,
    ).values('created_at', 'sentiment_score')

    if not notes:
        return {}

    df = pd.DataFrame(list(notes))
    df['date'] = pd.to_datetime(df['created_at']).dt.date

    grouped = df.groupby('date')['sentiment_score'].mean().round(2)
    return _sanitize({str(date): float(val) for date, val in grouped.items()})


def get_health_mood_correlation(user, days=30):
    """Correlate health metrics (steps, heart_rate, hrv, exercise) with daily mood."""
    from ..models import HealthMetric, MoodNote

    cutoff = timezone.localdate() - timedelta(days=days)

    # Get daily average sentiment
    notes = MoodNote.objects.filter(
        user=user, is_deleted=False,
        created_at__date__gte=cutoff,
        sentiment_score__isnull=False,
    ).values('created_at', 'sentiment_score')

    if not notes:
        return {}

    note_df = pd.DataFrame(list(notes))
    note_df['date'] = pd.to_datetime(note_df['created_at']).dt.date
    daily_mood = note_df.groupby('date')['sentiment_score'].mean()

    # Get health metrics
    metrics = HealthMetric.objects.filter(
        user=user, date__gte=cutoff,
    ).values('date', 'metric_type', 'value')

    if not metrics:
        return {}

    metric_df = pd.DataFrame(list(metrics))

    result = {}
    for metric_type in metric_df['metric_type'].unique():
        type_data = metric_df[metric_df['metric_type'] == metric_type].set_index('date')['value']

        # Join with mood data
        joined = pd.DataFrame({
            'metric': type_data,
            'sentiment': daily_mood,
        }).dropna()

        if len(joined) >= 3:
            try:
                r, p = stats.pearsonr(joined['metric'], joined['sentiment'])
                result[metric_type] = {
                    'correlation': round(r, 3),
                    'p_value': round(p, 4),
                    'sample_size': len(joined),
                    'scatter_data': [
                        {'value': float(row['metric']), 'sentiment': round(float(row['sentiment']), 3)}
                        for _, row in joined.iterrows()
                    ],
                }
            except Exception:
                # NaN / insufficient variance / shape mismatch — drop this metric,
                # the rest of the correlation report is still valuable.
                logger.warning('pearsonr failed for metric %s', metric_type, exc_info=True)

    return _sanitize(result)
