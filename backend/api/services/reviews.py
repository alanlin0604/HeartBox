from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q
from ..models import MoodNote


def get_on_this_day(user, date=None):
    """
    Get notes from previous years on this day (1 year ago, 2 years ago, etc.).
    Returns list of notes grouped by year.
    """
    if date is None:
        date = timezone.localdate()

    month = date.month
    day = date.day
    current_year = date.year

    # Get notes from same month/day in previous years (up to 10 years back)
    results = []
    for years_ago in range(1, 11):
        year = current_year - years_ago
        notes = MoodNote.objects.filter(
            user=user,
            is_deleted=False,
            created_at__year=year,
            created_at__month=month,
            created_at__day=day,
        ).order_by('-created_at')

        if notes.exists():
            # Get preview data (don't decrypt full content for performance)
            note_list = []
            for note in notes:
                note_list.append({
                    'id': note.id,
                    'preview': note.content_preview,
                    'sentiment_score': note.sentiment_score,
                    'stress_index': note.stress_index,
                    'created_at': note.created_at.isoformat(),
                    'metadata': note.metadata,
                })

            results.append({
                'years_ago': years_ago,
                'year': year,
                'date': f'{year}-{month:02d}-{day:02d}',
                'note_count': len(note_list),
                'notes': note_list,
            })

    return results


def get_monthly_review(user, year, month):
    """
    Generate a monthly review with statistics and highlights.
    """
    notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__year=year,
        created_at__month=month,
    )

    if not notes.exists():
        return None

    # Basic stats
    stats = notes.aggregate(
        total_notes=Count('id'),
        avg_sentiment=Avg('sentiment_score'),
        avg_stress=Avg('stress_index'),
    )

    # Sentiment distribution
    positive_count = notes.filter(sentiment_score__gte=0.3).count()
    neutral_count = notes.filter(sentiment_score__lt=0.3, sentiment_score__gt=-0.3).count()
    negative_count = notes.filter(sentiment_score__lte=-0.3).count()

    # Best and worst days
    best_day = notes.filter(sentiment_score__isnull=False).order_by('-sentiment_score').first()
    worst_day = notes.filter(sentiment_score__isnull=False).order_by('sentiment_score').first()

    # Tag analysis
    tag_counts = {}
    for note in notes.prefetch_related('tags'):
        for tag in note.tags.all():
            tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1

    # Also count legacy metadata tags
    for meta in notes.values_list('metadata', flat=True):
        tags = (meta or {}).get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        'year': year,
        'month': month,
        'total_notes': stats['total_notes'],
        'avg_sentiment': round(stats['avg_sentiment'], 2) if stats['avg_sentiment'] else None,
        'avg_stress': round(stats['avg_stress'], 1) if stats['avg_stress'] else None,
        'sentiment_distribution': {
            'positive': positive_count,
            'neutral': neutral_count,
            'negative': negative_count,
        },
        'best_day': {
            'id': best_day.id,
            'date': best_day.created_at.date().isoformat(),
            'sentiment': best_day.sentiment_score,
            'preview': best_day.content_preview,
        } if best_day else None,
        'worst_day': {
            'id': worst_day.id,
            'date': worst_day.created_at.date().isoformat(),
            'sentiment': worst_day.sentiment_score,
            'preview': worst_day.content_preview,
        } if worst_day else None,
        'top_tags': [{'name': tag, 'count': count} for tag, count in top_tags],
    }


def get_yearly_review(user, year):
    """
    Generate a yearly review (Year in Review) with comprehensive statistics.
    """
    notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__year=year,
    )

    if not notes.exists():
        return None

    # Basic stats
    stats = notes.aggregate(
        total_notes=Count('id'),
        avg_sentiment=Avg('sentiment_score'),
        avg_stress=Avg('stress_index'),
    )

    # Monthly breakdown
    monthly_data = []
    for month in range(1, 13):
        month_notes = notes.filter(created_at__month=month)
        if month_notes.exists():
            month_stats = month_notes.aggregate(
                count=Count('id'),
                avg_sentiment=Avg('sentiment_score'),
                avg_stress=Avg('stress_index'),
            )
            monthly_data.append({
                'month': month,
                'count': month_stats['count'],
                'avg_sentiment': round(month_stats['avg_sentiment'], 2) if month_stats['avg_sentiment'] else None,
                'avg_stress': round(month_stats['avg_stress'], 1) if month_stats['avg_stress'] else None,
            })

    # Sentiment distribution
    positive_count = notes.filter(sentiment_score__gte=0.3).count()
    neutral_count = notes.filter(sentiment_score__lt=0.3, sentiment_score__gt=-0.3).count()
    negative_count = notes.filter(sentiment_score__lte=-0.3).count()

    # Best month
    best_month_data = None
    best_avg = -2
    for month_data in monthly_data:
        if month_data['avg_sentiment'] and month_data['avg_sentiment'] > best_avg:
            best_avg = month_data['avg_sentiment']
            best_month_data = month_data

    # Tag analysis
    tag_counts = {}
    for note in notes.prefetch_related('tags'):
        for tag in note.tags.all():
            tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1

    # Also count legacy metadata tags
    for meta in notes.values_list('metadata', flat=True):
        tags = (meta or {}).get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Most productive month (most notes)
    most_productive = max(monthly_data, key=lambda x: x['count']) if monthly_data else None

    return {
        'year': year,
        'total_notes': stats['total_notes'],
        'avg_sentiment': round(stats['avg_sentiment'], 2) if stats['avg_sentiment'] else None,
        'avg_stress': round(stats['avg_stress'], 1) if stats['avg_stress'] else None,
        'sentiment_distribution': {
            'positive': positive_count,
            'neutral': neutral_count,
            'negative': negative_count,
        },
        'monthly_breakdown': monthly_data,
        'best_month': best_month_data,
        'most_productive_month': most_productive,
        'top_tags': [{'name': tag, 'count': count} for tag, count in top_tags],
    }
