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

    # Tag filter (JSON contains)
    if tag:
        queryset = queryset.filter(metadata__tags__contains=[tag])

    # Keyword search — must decrypt, so do this last on the narrowed queryset
    if search:
        keyword = search.lower()
        matching_ids = []
        for note in queryset.iterator():
            try:
                if keyword in note.content.lower():
                    matching_ids.append(note.pk)
            except Exception:
                continue
        queryset = queryset.filter(pk__in=matching_ids)

    return queryset
