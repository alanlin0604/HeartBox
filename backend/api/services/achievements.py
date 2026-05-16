from django.utils import timezone

from api.models import (
    AIChatSession, Booking, Conversation,
    DailySleep, DashboardLayout, Feedback, Friendship, FriendComment,
    Habit, HabitLog, HealthMetric, Message, MoodNote, Notification,
    NoteAttachment, PostReaction, PublicPost, SelfAssessment, SharedNote,
    SharedWithFriend, UserAchievement, WellnessSession,
)

ACHIEVEMENT_DEFINITIONS = {
    # ===== Writing =====
    'first_note': {
        'category': 'writing',
        'icon': 'pencil',
        'threshold': 1,
        'name_key': 'achievement.first_note',
        'desc_key': 'achievement.first_note_desc',
    },
    'notes_10': {
        'category': 'writing',
        'icon': 'notebook',
        'threshold': 10,
        'name_key': 'achievement.notes_10',
        'desc_key': 'achievement.notes_10_desc',
    },
    'notes_50': {
        'category': 'writing',
        'icon': 'books',
        'threshold': 50,
        'name_key': 'achievement.notes_50',
        'desc_key': 'achievement.notes_50_desc',
    },
    'notes_100': {
        'category': 'writing',
        'icon': 'trophy',
        'threshold': 100,
        'name_key': 'achievement.notes_100',
        'desc_key': 'achievement.notes_100_desc',
    },
    'long_writer': {
        'category': 'writing',
        'icon': 'scroll',
        'threshold': 500,
        'name_key': 'achievement.long_writer',
        'desc_key': 'achievement.long_writer_desc',
    },
    # ===== Consistency =====
    'streak_3': {
        'category': 'consistency',
        'icon': 'fire',
        'threshold': 3,
        'name_key': 'achievement.streak_3',
        'desc_key': 'achievement.streak_3_desc',
    },
    'streak_7': {
        'category': 'consistency',
        'icon': 'flame',
        'threshold': 7,
        'name_key': 'achievement.streak_7',
        'desc_key': 'achievement.streak_7_desc',
    },
    'streak_30': {
        'category': 'consistency',
        'icon': 'calendar',
        'threshold': 30,
        'name_key': 'achievement.streak_30',
        'desc_key': 'achievement.streak_30_desc',
    },
    # ===== Mood =====
    'mood_explorer': {
        'category': 'mood',
        'icon': 'compass',
        'threshold': 5,
        'name_key': 'achievement.mood_explorer',
        'desc_key': 'achievement.mood_explorer_desc',
    },
    'positive_streak': {
        'category': 'mood',
        'icon': 'sun',
        'threshold': 3,
        'name_key': 'achievement.positive_streak',
        'desc_key': 'achievement.positive_streak_desc',
    },
    'mood_improver': {
        'category': 'mood',
        'icon': 'trending_up',
        'threshold': 3,
        'name_key': 'achievement.mood_improver',
        'desc_key': 'achievement.mood_improver_desc',
    },
    'self_aware': {
        'category': 'mood',
        'icon': 'brain',
        'threshold': 10,
        'name_key': 'achievement.self_aware',
        'desc_key': 'achievement.self_aware_desc',
    },
    # ===== Social =====
    'first_share': {
        'category': 'social',
        'icon': 'share',
        'threshold': 1,
        'name_key': 'achievement.first_share',
        'desc_key': 'achievement.first_share_desc',
    },
    'first_booking': {
        'category': 'social',
        'icon': 'calendar_check',
        'threshold': 1,
        'name_key': 'achievement.first_booking',
        'desc_key': 'achievement.first_booking_desc',
    },
    'first_ai_chat': {
        'category': 'social',
        'icon': 'robot',
        'threshold': 1,
        'name_key': 'achievement.first_ai_chat',
        'desc_key': 'achievement.first_ai_chat_desc',
    },
    'ai_chat_10': {
        'category': 'social',
        'icon': 'chat_dots',
        'threshold': 10,
        'name_key': 'achievement.ai_chat_10',
        'desc_key': 'achievement.ai_chat_10_desc',
    },
    # ===== Explore =====
    'night_owl': {
        'category': 'explore',
        'icon': 'moon',
        'threshold': 1,
        'name_key': 'achievement.night_owl',
        'desc_key': 'achievement.night_owl_desc',
    },
    'early_bird': {
        'category': 'explore',
        'icon': 'sunrise',
        'threshold': 1,
        'name_key': 'achievement.early_bird',
        'desc_key': 'achievement.early_bird_desc',
    },
    'pin_master': {
        'category': 'explore',
        'icon': 'pin',
        'threshold': 5,
        'name_key': 'achievement.pin_master',
        'desc_key': 'achievement.pin_master_desc',
    },
    # ===== New Achievements =====
    'notes_200': {
        'category': 'writing',
        'icon': 'medal',
        'threshold': 200,
        'name_key': 'achievement.notes_200',
        'desc_key': 'achievement.notes_200_desc',
    },
    'first_image': {
        'category': 'writing',
        'icon': 'camera',
        'threshold': 1,
        'name_key': 'achievement.first_image',
        'desc_key': 'achievement.first_image_desc',
    },
    'weekend_warrior': {
        'category': 'consistency',
        'icon': 'sparkles',
        'threshold': 1,
        'name_key': 'achievement.weekend_warrior',
        'desc_key': 'achievement.weekend_warrior_desc',
    },
    'dedicated_months_3': {
        'category': 'consistency',
        'icon': 'calendar_star',
        'threshold': 3,
        'name_key': 'achievement.dedicated_months_3',
        'desc_key': 'achievement.dedicated_months_3_desc',
    },
    'stress_manager': {
        'category': 'mood',
        'icon': 'leaf',
        'threshold': 5,
        'name_key': 'achievement.stress_manager',
        'desc_key': 'achievement.stress_manager_desc',
    },
    'emotional_range': {
        'category': 'mood',
        'icon': 'rainbow',
        'threshold': 2,
        'name_key': 'achievement.emotional_range',
        'desc_key': 'achievement.emotional_range_desc',
    },
    'conversation_starter': {
        'category': 'social',
        'icon': 'handshake',
        'threshold': 1,
        'name_key': 'achievement.conversation_starter',
        'desc_key': 'achievement.conversation_starter_desc',
    },
    'messages_50': {
        'category': 'social',
        'icon': 'mailbox',
        'threshold': 50,
        'name_key': 'achievement.messages_50',
        'desc_key': 'achievement.messages_50_desc',
    },
    'tag_collector': {
        'category': 'explore',
        'icon': 'tags',
        'threshold': 10,
        'name_key': 'achievement.tag_collector',
        'desc_key': 'achievement.tag_collector_desc',
    },
    'weather_logger': {
        'category': 'explore',
        'icon': 'cloud_sun',
        'threshold': 5,
        'name_key': 'achievement.weather_logger',
        'desc_key': 'achievement.weather_logger_desc',
    },
    'feedback_giver': {
        'category': 'wellness',
        'icon': 'heart',
        'threshold': 1,
        'name_key': 'achievement.feedback_giver',
        'desc_key': 'achievement.feedback_giver_desc',
    },

    # ===== NEW: Friends Category =====
    'first_friend': {
        'category': 'friends',
        'icon': 'user_plus',
        'threshold': 1,
        'name_key': 'achievement.first_friend',
        'desc_key': 'achievement.first_friend_desc',
    },
    'friends_5': {
        'category': 'friends',
        'icon': 'users',
        'threshold': 5,
        'name_key': 'achievement.friends_5',
        'desc_key': 'achievement.friends_5_desc',
    },
    'first_friend_share': {
        'category': 'friends',
        'icon': 'gift',
        'threshold': 1,
        'name_key': 'achievement.first_friend_share',
        'desc_key': 'achievement.first_friend_share_desc',
    },
    'friend_supporter': {
        'category': 'friends',
        'icon': 'message_heart',
        'threshold': 5,
        'name_key': 'achievement.friend_supporter',
        'desc_key': 'achievement.friend_supporter_desc',
    },

    # ===== NEW: Community Category =====
    'first_community_post': {
        'category': 'community',
        'icon': 'megaphone',
        'threshold': 1,
        'name_key': 'achievement.first_community_post',
        'desc_key': 'achievement.first_community_post_desc',
    },
    'community_supporter': {
        'category': 'community',
        'icon': 'hands_helping',
        'threshold': 10,
        'name_key': 'achievement.community_supporter',
        'desc_key': 'achievement.community_supporter_desc',
    },
    'community_voice': {
        'category': 'community',
        'icon': 'sparkle_heart',
        'threshold': 5,
        'name_key': 'achievement.community_voice',
        'desc_key': 'achievement.community_voice_desc',
    },

    # ===== NEW: Health Category =====
    'first_sleep_log': {
        'category': 'health',
        'icon': 'bed',
        'threshold': 1,
        'name_key': 'achievement.first_sleep_log',
        'desc_key': 'achievement.first_sleep_log_desc',
    },
    'sleep_streak_7': {
        'category': 'health',
        'icon': 'moon_stars',
        'threshold': 7,
        'name_key': 'achievement.sleep_streak_7',
        'desc_key': 'achievement.sleep_streak_7_desc',
    },
    'quality_sleeper': {
        'category': 'health',
        'icon': 'star_filled',
        'threshold': 1,
        'name_key': 'achievement.quality_sleeper',
        'desc_key': 'achievement.quality_sleeper_desc',
    },
    'first_health_sync': {
        'category': 'health',
        'icon': 'watch',
        'threshold': 1,
        'name_key': 'achievement.first_health_sync',
        'desc_key': 'achievement.first_health_sync_desc',
    },
    'step_goal_10k': {
        'category': 'health',
        'icon': 'footprints',
        'threshold': 1,
        'name_key': 'achievement.step_goal_10k',
        'desc_key': 'achievement.step_goal_10k_desc',
    },

    # ===== NEW: Wellness expanded (habits + breathing) =====
    'first_habit': {
        'category': 'wellness',
        'icon': 'target',
        'threshold': 1,
        'name_key': 'achievement.first_habit',
        'desc_key': 'achievement.first_habit_desc',
    },
    'habit_streak_7': {
        'category': 'wellness',
        'icon': 'flame_small',
        'threshold': 7,
        'name_key': 'achievement.habit_streak_7',
        'desc_key': 'achievement.habit_streak_7_desc',
    },
    'habit_streak_30': {
        'category': 'wellness',
        'icon': 'crown',
        'threshold': 30,
        'name_key': 'achievement.habit_streak_30',
        'desc_key': 'achievement.habit_streak_30_desc',
    },
    'first_breathing': {
        'category': 'wellness',
        'icon': 'lungs',
        'threshold': 1,
        'name_key': 'achievement.first_breathing',
        'desc_key': 'achievement.first_breathing_desc',
    },
    'wellness_sessions_10': {
        'category': 'wellness',
        'icon': 'lotus',
        'threshold': 10,
        'name_key': 'achievement.wellness_sessions_10',
        'desc_key': 'achievement.wellness_sessions_10_desc',
    },

    # ===== NEW: Explore expanded =====
    'first_assessment': {
        'category': 'explore',
        'icon': 'clipboard_check',
        'threshold': 1,
        'name_key': 'achievement.first_assessment',
        'desc_key': 'achievement.first_assessment_desc',
    },
    'assessment_regular': {
        'category': 'explore',
        'icon': 'graph_up',
        'threshold': 5,
        'name_key': 'achievement.assessment_regular',
        'desc_key': 'achievement.assessment_regular_desc',
    },
    'dashboard_customized': {
        'category': 'explore',
        'icon': 'layout',
        'threshold': 1,
        'name_key': 'achievement.dashboard_customized',
        'desc_key': 'achievement.dashboard_customized_desc',
    },
    'ai_chat_50': {
        'category': 'social',
        'icon': 'robot_star',
        'threshold': 50,
        'name_key': 'achievement.ai_chat_50',
        'desc_key': 'achievement.ai_chat_50_desc',
    },

    # ===== NEW: Meta achievements =====
    'achievement_hunter': {
        'category': 'meta',
        'icon': 'medal_bronze',
        'threshold': 10,
        'name_key': 'achievement.achievement_hunter',
        'desc_key': 'achievement.achievement_hunter_desc',
    },
    'achievement_legend': {
        'category': 'meta',
        'icon': 'medal_gold',
        'threshold': 25,
        'name_key': 'achievement.achievement_legend',
        'desc_key': 'achievement.achievement_legend_desc',
    },
}


def _get_note_count(user):
    return MoodNote.objects.filter(user=user, is_deleted=False).count()


def _get_longest_streak(user):
    dates = list(
        MoodNote.objects.filter(user=user, is_deleted=False)
        .values_list('created_at__date', flat=True)
        .distinct()
        .order_by('-created_at__date')[:366]
    )
    if not dates:
        return 0
    sorted_dates = sorted(set(dates))
    best = 1
    run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _get_max_note_length(user):
    """Get max character count of any note using search_text (plaintext, up to 500 chars)."""
    from django.db.models.functions import Length
    result = (
        MoodNote.objects.filter(user=user, is_deleted=False)
        .exclude(search_text='')
        .annotate(text_len=Length('search_text'))
        .order_by('-text_len')
        .values_list('text_len', flat=True)
        .first()
    )
    return result or 0


def _get_distinct_mood_buckets(user):
    """Count distinct mood buckets used: very_negative, negative, neutral, positive, very_positive."""
    scores = list(
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .values_list('sentiment_score', flat=True)
    )
    buckets = set()
    for s in scores:
        if s <= -0.6:
            buckets.add('very_negative')
        elif s <= -0.2:
            buckets.add('negative')
        elif s <= 0.2:
            buckets.add('neutral')
        elif s <= 0.6:
            buckets.add('positive')
        else:
            buckets.add('very_positive')
    return len(buckets)


def _has_positive_streak(user, count=3):
    """Check if last `count` notes all have positive sentiment (>0.3)."""
    scores = list(
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .order_by('-created_at')
        .values_list('sentiment_score', flat=True)[:count]
    )
    return len(scores) >= count and all(s > 0.3 for s in scores)


def _has_mood_improving(user, count=3):
    """Check if last `count` notes have consecutively increasing sentiment."""
    scores = list(
        MoodNote.objects.filter(user=user, sentiment_score__isnull=False)
        .order_by('-created_at')
        .values_list('sentiment_score', flat=True)[:count]
    )
    if len(scores) < count:
        return False
    # Reverse so oldest first
    scores = scores[::-1]
    return all(scores[i] < scores[i + 1] for i in range(len(scores) - 1))


def _get_ai_analyzed_count(user):
    return MoodNote.objects.filter(user=user, ai_feedback__gt='').count()


def _has_weekend_pair(user):
    """Check if the user has written notes on both Saturday and Sunday of the same week."""
    dates = list(
        MoodNote.objects.filter(user=user, is_deleted=False)
        .values_list('created_at__date', flat=True)
        .distinct()
        .order_by('created_at__date')
    )
    # Group by ISO week
    weeks = {}
    for d in dates:
        key = (d.isocalendar()[0], d.isocalendar()[1])
        weeks.setdefault(key, set()).add(d.isoweekday())
    # isoweekday: 6=Saturday, 7=Sunday
    return any(6 in days and 7 in days for days in weeks.values())


def _get_distinct_tag_count(user):
    """Count distinct tags across all notes (only recent 500 for performance)."""
    tags = set()
    for meta in MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').values_list('metadata', flat=True)[:500]:
        if meta and isinstance(meta, dict):
            for tag in (meta.get('tags') or []):
                tags.add(tag)
    return len(tags)


def _get_weather_note_count(user):
    """Count notes that have a non-empty weather field."""
    count = 0
    for meta in MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').values_list('metadata', flat=True)[:500]:
        if meta and isinstance(meta, dict) and meta.get('weather'):
            count += 1
    return count


def _get_longest_sleep_streak(user):
    """Longest consecutive-day streak of DailySleep records."""
    dates = list(
        DailySleep.objects.filter(user=user).values_list('date', flat=True).order_by('date')[:366]
    )
    if not dates:
        return 0
    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _get_quality_sleep_week(user):
    """1 if any 7-day window has avg sleep_quality >= 4, else 0."""
    from datetime import timedelta
    qualities = list(
        DailySleep.objects.filter(user=user, sleep_quality__isnull=False)
        .order_by('-date').values_list('date', 'sleep_quality')[:60]
    )
    if len(qualities) < 7:
        return 0
    # Group by date for rolling window
    date_to_q = {d: q for d, q in qualities}
    sorted_dates = sorted(date_to_q.keys())
    for i in range(len(sorted_dates) - 6):
        window = [
            date_to_q[d] for d in sorted_dates[i:i + 7]
            if (sorted_dates[i + 6] - sorted_dates[i]).days == 6
        ]
        if len(window) == 7 and sum(window) / 7 >= 4.0:
            return 1
    return 0


def _get_longest_habit_streak(user):
    """Across all of the user's habits, the longest single-habit consecutive-day streak."""
    habits = Habit.objects.filter(user=user, is_active=True).values_list('id', flat=True)
    best = 0
    for habit_id in habits:
        dates = list(
            HabitLog.objects.filter(habit_id=habit_id).values_list('date', flat=True).order_by('date')[:400]
        )
        if not dates:
            continue
        run = 1
        local_best = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                run += 1
                local_best = max(local_best, run)
            else:
                run = 1
        best = max(best, local_best)
    return best


_PROGRESS_CACHE_TTL = 30  # seconds — short enough to feel "live", long enough to dedupe a page load


def _progress_cache_key(user):
    return f'ach_progress:{user.id}'


def invalidate_progress_cache(user):
    """Call after any state change that could affect achievement progress.

    Most progress changes flow through ``check_achievements`` (which
    invalidates internally), but external mutation paths can call this
    directly to avoid the user seeing stale numbers.
    """
    from django.core.cache import cache
    cache.delete(_progress_cache_key(user))


def _get_progress(user):
    """Calculate progress for all achievements. Returns dict of achievement_id -> current value.

    Result is cached for ~30 s per user. Multiple endpoints on the same
    page load (``/achievements/`` + ``/achievements/check/`` historically)
    re-aggregated 15+ tables on every hit; the cache collapses repeat
    work to a single DB pass within the cache window.
    """
    from django.core.cache import cache
    from django.db.models import Count, Q

    cache_key = _progress_cache_key(user)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # --- Batch 1: Aggregate MoodNote counts in a single query ---
    note_agg = MoodNote.objects.filter(user=user).aggregate(
        note_count=Count('id', filter=Q(is_deleted=False)),
        pinned_count=Count('id', filter=Q(is_pinned=True)),
        ai_analyzed=Count('id', filter=Q(ai_feedback__gt='')),
        has_night=Count('id', filter=Q(created_at__hour__gte=0, created_at__hour__lt=5)),
        has_early=Count('id', filter=Q(created_at__hour__gte=5, created_at__hour__lt=7)),
        low_stress_count=Count('id', filter=Q(stress_index__isnull=False, stress_index__lte=3)),
        has_high_sentiment=Count('id', filter=Q(sentiment_score__gt=0.6)),
        has_low_sentiment=Count('id', filter=Q(sentiment_score__lt=-0.6)),
    )
    note_count = note_agg['note_count']

    # Max note length (separate query - Length is not an aggregate function)
    max_len = _get_max_note_length(user)

    longest_streak = _get_longest_streak(user)

    # --- Batch 2: Aggregate other model counts in single queries ---
    other_counts = {
        'share_count': SharedNote.objects.filter(note__user=user).count(),
        'booking_count': Booking.objects.filter(user=user).count(),
        'ai_session_count': AIChatSession.objects.filter(user=user).count(),
        'conversation_count': Conversation.objects.filter(user=user).count(),
        'message_count': Message.objects.filter(sender=user).count(),
        'feedback_count': Feedback.objects.filter(user=user).count(),
        'image_count': NoteAttachment.objects.filter(note__user=user, file_type='image').count(),
    }

    has_weekend = _has_weekend_pair(user)
    distinct_months = MoodNote.objects.filter(user=user, is_deleted=False).dates('created_at', 'month').count()
    mood_buckets = _get_distinct_mood_buckets(user)
    tag_count = _get_distinct_tag_count(user)
    weather_count = _get_weather_note_count(user)

    emotional_range = (1 if note_agg['has_high_sentiment'] > 0 else 0) + (1 if note_agg['has_low_sentiment'] > 0 else 0)

    # --- Batch 3: New feature counters ---
    new_counts = {
        'friend_count': Friendship.objects.filter(user=user).count(),
        'friend_share_count': SharedWithFriend.objects.filter(shared_by=user).count(),
        'friend_comment_count': FriendComment.objects.filter(commenter=user).count(),
        'community_posts': PublicPost.objects.filter(user=user, is_active=True).count(),
        'community_reactions_given': PostReaction.objects.filter(user=user).count(),
        'community_reactions_received': PostReaction.objects.filter(post__user=user).count(),
        'sleep_logs': DailySleep.objects.filter(user=user).count(),
        # Non-manual = synced from Health Connect / Apple Health
        'health_synced': HealthMetric.objects.filter(user=user).exclude(source='manual').count(),
        'habits_count': Habit.objects.filter(user=user, is_active=True).count(),
        'assessments_count': SelfAssessment.objects.filter(user=user).count(),
        'wellness_sessions': WellnessSession.objects.filter(user=user).count(),
        # DashboardLayout exists ⇒ user customized at least once
        'dashboard_customized': 1 if DashboardLayout.objects.filter(user=user).exists() else 0,
    }
    # Single-day step goal 10k
    step_10k_hit = HealthMetric.objects.filter(
        user=user, metric_type='steps', value__gte=10000,
    ).exists()
    longest_sleep_streak = _get_longest_sleep_streak(user)
    longest_habit_streak = _get_longest_habit_streak(user)
    quality_sleep_hit = _get_quality_sleep_week(user)

    # Meta: count of currently-unlocked achievements
    # (computed BEFORE this run's unlocks — the check_achievements caller
    # will re-run if any meta achievements just crossed their threshold.)
    unlocked_count = UserAchievement.objects.filter(user=user).count()

    result = {
        'first_note': note_count,
        'notes_10': note_count,
        'notes_50': note_count,
        'notes_100': note_count,
        'long_writer': max_len,
        'streak_3': longest_streak,
        'streak_7': longest_streak,
        'streak_30': longest_streak,
        'mood_explorer': mood_buckets,
        'positive_streak': 3 if _has_positive_streak(user) else 0,
        'mood_improver': 3 if _has_mood_improving(user) else 0,
        'self_aware': note_agg['ai_analyzed'],
        'first_share': other_counts['share_count'],
        'first_booking': other_counts['booking_count'],
        'first_ai_chat': other_counts['ai_session_count'],
        'ai_chat_10': other_counts['ai_session_count'],
        'night_owl': 1 if note_agg['has_night'] > 0 else 0,
        'early_bird': 1 if note_agg['has_early'] > 0 else 0,
        'pin_master': note_agg['pinned_count'],
        # New achievements
        'notes_200': note_count,
        'first_image': other_counts['image_count'],
        'weekend_warrior': 1 if has_weekend else 0,
        'dedicated_months_3': distinct_months,
        'stress_manager': note_agg['low_stress_count'],
        'emotional_range': emotional_range,
        'conversation_starter': other_counts['conversation_count'],
        'messages_50': other_counts['message_count'],
        'tag_collector': tag_count,
        'weather_logger': weather_count,
        'feedback_giver': other_counts['feedback_count'],
        # NEW: friends
        'first_friend': new_counts['friend_count'],
        'friends_5': new_counts['friend_count'],
        'first_friend_share': new_counts['friend_share_count'],
        'friend_supporter': new_counts['friend_comment_count'],
        # NEW: community
        'first_community_post': new_counts['community_posts'],
        'community_supporter': new_counts['community_reactions_given'],
        'community_voice': new_counts['community_reactions_received'],
        # NEW: health
        'first_sleep_log': new_counts['sleep_logs'],
        'sleep_streak_7': longest_sleep_streak,
        'quality_sleeper': quality_sleep_hit,
        'first_health_sync': new_counts['health_synced'],
        'step_goal_10k': 1 if step_10k_hit else 0,
        # NEW: wellness expanded
        'first_habit': new_counts['habits_count'],
        'habit_streak_7': longest_habit_streak,
        'habit_streak_30': longest_habit_streak,
        'first_breathing': new_counts['wellness_sessions'],
        'wellness_sessions_10': new_counts['wellness_sessions'],
        # NEW: explore expanded
        'first_assessment': new_counts['assessments_count'],
        'assessment_regular': new_counts['assessments_count'],
        'dashboard_customized': new_counts['dashboard_customized'],
        'ai_chat_50': other_counts['ai_session_count'],
        # NEW: meta (compares against the OTHER achievements unlocked)
        'achievement_hunter': unlocked_count,
        'achievement_legend': unlocked_count,
    }
    cache.set(cache_key, result, _PROGRESS_CACHE_TTL)
    return result


def check_achievements(user):
    """Check all achievement conditions and unlock any new ones.

    Two-pass: meta achievements (achievement_hunter, achievement_legend)
    count *currently-unlocked* achievements. When a single call unlocks
    several normal achievements, the meta count needs to reflect the new
    total. We loop until no new unlocks happen (capped at 5 iterations
    to defend against bugs causing an unlock loop).
    """
    # Mutations may have happened since the last cache snapshot — start
    # fresh so we don't miss a threshold the caller's action just crossed.
    invalidate_progress_cache(user)
    newly_unlocked = []
    for _iteration in range(5):
        existing = set(
            UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
        )
        progress = _get_progress(user)
        unlocked_this_pass = []
        for aid, defn in ACHIEVEMENT_DEFINITIONS.items():
            if aid in existing:
                continue
            current = progress.get(aid, 0)
            if current >= defn['threshold']:
                UserAchievement.objects.create(user=user, achievement_id=aid)
                unlocked_this_pass.append(aid)
        if not unlocked_this_pass:
            break
        # Meta achievements count unlocks — invalidate before the next pass.
        invalidate_progress_cache(user)
        newly_unlocked.extend(unlocked_this_pass)
    # Surface each unlock as a Notification so the WebSocket fan-out
    # delivers a real-time toast wherever the user is in the app —
    # the previous flow only showed a toast on the Achievements page.
    if newly_unlocked:
        _emit_unlock_notifications(user, newly_unlocked)
    return newly_unlocked


def _emit_unlock_notifications(user, achievement_ids):
    """Create + fan out a Notification for each newly unlocked achievement.

    Translation of the title/body is done client-side via the achievement
    id stored in ``data.achievement_id`` — the message field carries a
    fallback string for clients that don't translate.
    """
    for aid in achievement_ids:
        defn = ACHIEVEMENT_DEFINITIONS.get(aid, {})
        notification = Notification.objects.create(
            user=user,
            type='achievement',
            title='Achievement unlocked',
            message=aid,
            data={
                'achievement_id': aid,
                'category': defn.get('category', ''),
                'icon': defn.get('icon', 'trophy'),
            },
        )
        # Best-effort WS push — same pattern as save_message in consumers.py.
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            layer = get_channel_layer()
            if layer is not None:
                async_to_sync(layer.group_send)(
                    f'notifications_{user.id}',
                    {
                        'type': 'notify',
                        'data': {
                            'id': notification.id,
                            'type': notification.type,
                            'title': notification.title,
                            'message': notification.message,
                            'data': notification.data,
                            'is_read': False,
                            'created_at': notification.created_at.isoformat(),
                        },
                    },
                )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'Achievement notification fan-out failed user=%s aid=%s', user.id, aid,
            )
        # Also fire a web-push so users see the unlock when they're not
        # actively in the tab. Wrapped in try so a missing VAPID key or a
        # 410 from a stale subscription never blocks the achievement save.
        try:
            from api.views import send_push_notification
            send_push_notification(
                user,
                'Achievement unlocked',
                aid,
                url='/achievements',
            )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'Achievement push failed user=%s aid=%s', user.id, aid,
            )


def get_user_achievements_with_progress(user):
    """Return all achievements with progress info and unlock status."""
    unlocked = {
        ua.achievement_id: ua.unlocked_at
        for ua in UserAchievement.objects.filter(user=user)
    }
    progress = _get_progress(user)

    result = []
    for aid, defn in ACHIEVEMENT_DEFINITIONS.items():
        current = progress.get(aid, 0)
        threshold = defn['threshold']
        result.append({
            'id': aid,
            'category': defn['category'],
            'icon': defn['icon'],
            'name_key': defn['name_key'],
            'desc_key': defn['desc_key'],
            'threshold': threshold,
            'current': min(current, threshold),
            'unlocked': aid in unlocked,
            'unlocked_at': unlocked.get(aid),
        })
    return result
