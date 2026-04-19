from datetime import datetime


def search_notes(queryset, search=None, tag=None,
                 sentiment_min=None, sentiment_max=None,
                 stress_min=None, stress_max=None,
                 date_from=None, date_to=None):
    """
    Filter MoodNote queryset using structured fields first (DB-level),
    then decrypt-and-match keyword search as the final step.
    """
    # Date range filters
    if date_from:
        try:
            dt = datetime.strptime(date_from, '%Y-%m-%d')
            queryset = queryset.filter(created_at__date__gte=dt.date())
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            queryset = queryset.filter(created_at__date__lte=dt.date())
        except ValueError:
            pass

    # Sentiment range filters
    if sentiment_min is not None:
        try:
            queryset = queryset.filter(sentiment_score__gte=float(sentiment_min))
        except (ValueError, TypeError):
            pass

    if sentiment_max is not None:
        try:
            queryset = queryset.filter(sentiment_score__lte=float(sentiment_max))
        except (ValueError, TypeError):
            pass

    # Stress range filters
    if stress_min is not None:
        try:
            queryset = queryset.filter(stress_index__gte=int(stress_min))
        except (ValueError, TypeError):
            pass

    if stress_max is not None:
        try:
            queryset = queryset.filter(stress_index__lte=int(stress_max))
        except (ValueError, TypeError):
            pass

    # Tag filter - supports both new Tag model (by name or ID) and legacy metadata tags
    if tag:
        # Try filtering by Tag model first (many-to-many relationship)
        try:
            # If tag is a digit, treat as tag ID
            if tag.isdigit():
                queryset = queryset.filter(tags__id=int(tag))
            else:
                # Otherwise, treat as tag name
                queryset = queryset.filter(tags__name__iexact=tag)
        except Exception:
            # Fallback to legacy metadata tags (JSON contains)
            queryset = queryset.filter(metadata__tags__contains=[tag])

    # Keyword search — DB-level via search_text index
    if search:
        queryset = queryset.filter(search_text__icontains=search)

    return queryset.distinct()
