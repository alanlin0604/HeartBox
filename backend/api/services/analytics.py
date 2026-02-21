from datetime import timedelta

import pandas as pd
from django.db.models import Avg
from django.utils import timezone
from scipy import stats


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
        iso = df['date'].dt.isocalendar()
        df['period'] = iso.year.astype(str) + '-W' + iso.week.astype(str).str.zfill(2)
        df['sort_key'] = df['period']
    else:  # month
        df['period'] = df['date'].dt.strftime('%Y-%m')
        df['sort_key'] = df['date'].dt.to_period('M').astype(str)

    grouped = df.groupby('period').agg(
        avg_sentiment=('sentiment_score', 'mean'),
        avg_stress=('stress_index', 'mean'),
        count=('sentiment_score', 'count'),
    ).reset_index()

    grouped['avg_sentiment'] = grouped['avg_sentiment'].round(2)
    grouped['avg_stress'] = grouped['avg_stress'].round(1)

    return grouped.rename(columns={'period': 'name'}).to_dict(orient='records')


def get_mood_weather_correlation(queryset, lookback_days=90):
    """Pearson correlation between sentiment and temperature + heatmap buckets."""
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
        return {'correlation': None, 'p_value': None, 'scatter_data': pairs, 'sample_size': len(pairs)}

    df = pd.DataFrame(pairs)
    try:
        r, p = stats.pearsonr(df['sentiment'], df['temperature'])
    except Exception:
        return {'correlation': None, 'p_value': None, 'scatter_data': pairs, 'sample_size': len(pairs)}

    # Heatmap buckets (temp ranges × sentiment ranges)
    temp_bins = pd.cut(df['temperature'], bins=5, labels=False)
    sent_bins = pd.cut(df['sentiment'], bins=5, labels=False)
    heatmap = df.assign(temp_bin=temp_bins, sent_bin=sent_bins)\
        .groupby(['temp_bin', 'sent_bin']).size().reset_index(name='count')

    return {
        'correlation': round(r, 3),
        'p_value': round(p, 4),
        'scatter_data': pairs,
        'heatmap': heatmap.to_dict(orient='records'),
        'sample_size': len(pairs),
    }


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

    return grouped.to_dict(orient='records')


def get_frequent_tags(queryset, lookback_days=90, top_n=10):
    """Aggregate tag frequency from metadata.tags. Returns Recharts BarChart data."""
    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(created_at__gte=since).values('metadata')

    tag_counts = {}
    for note in notes:
        meta = note.get('metadata') or {}
        tags = meta.get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{'name': tag, 'count': count} for tag, count in sorted_tags]


def get_stress_by_tag(queryset, lookback_days=90):
    """Average stress index per tag for RadarChart. Returns [{tag, avg_stress, count}]."""
    since = timezone.now() - timedelta(days=lookback_days)
    notes = queryset.filter(
        created_at__gte=since,
        stress_index__isnull=False,
    ).values('stress_index', 'metadata')

    tag_stress = {}  # tag -> [stress_values]
    for note in notes:
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
    return result


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
    return {str(date): float(val) for date, val in grouped.items()}
