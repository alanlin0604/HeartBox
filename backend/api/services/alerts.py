from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone


def check_mood_alerts(queryset):
    """
    Check for three mood alert patterns:
    1. Consecutive negative: last 3+ notes have sentiment < -0.3
    2. High stress: average stress > 7 over the past 7 days
    3. Sudden drop: avg sentiment dropped > 0.5 (recent 3 days vs prior 7 days)
    """
    alerts = []
    now = timezone.now()

    # --- 1. Consecutive negative ---
    recent_notes = list(
        queryset.filter(sentiment_score__isnull=False)
        .order_by('-created_at')
        .values_list('sentiment_score', flat=True)[:10]
    )

    consecutive_negative = 0
    for score in recent_notes:
        if score < -0.3:
            consecutive_negative += 1
        else:
            break

    if consecutive_negative >= 3:
        severity = 'high' if consecutive_negative >= 5 else 'medium'
        alerts.append({
            'type': 'consecutive_negative',
            'severity': severity,
            'data': {'count': consecutive_negative},
        })

    # --- 2. High stress (past 7 days) ---
    week_ago = now - timedelta(days=7)
    stress_avg = queryset.filter(
        created_at__gte=week_ago,
        stress_index__isnull=False,
    ).aggregate(avg=Avg('stress_index'))['avg']

    if stress_avg is not None and stress_avg > 7:
        alerts.append({
            'type': 'high_stress',
            'severity': 'high',
            'data': {'avg_stress': round(stress_avg, 1)},
        })

    # --- 3. Sudden sentiment drop ---
    three_days_ago = now - timedelta(days=3)
    ten_days_ago = now - timedelta(days=10)

    recent_avg = queryset.filter(
        created_at__gte=three_days_ago,
        sentiment_score__isnull=False,
    ).aggregate(avg=Avg('sentiment_score'))['avg']

    prior_avg = queryset.filter(
        created_at__gte=ten_days_ago,
        created_at__lt=three_days_ago,
        sentiment_score__isnull=False,
    ).aggregate(avg=Avg('sentiment_score'))['avg']

    if recent_avg is not None and prior_avg is not None:
        drop = prior_avg - recent_avg
        if drop > 0.5:
            severity = 'high' if drop > 0.8 else 'medium'
            alerts.append({
                'type': 'sudden_drop',
                'severity': severity,
                'data': {
                    'recent_avg': round(recent_avg, 2),
                    'prior_avg': round(prior_avg, 2),
                    'drop': round(drop, 2),
                },
            })

    return alerts
