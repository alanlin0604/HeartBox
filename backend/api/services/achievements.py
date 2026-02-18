from django.db.models import Count, Q
from django.utils import timezone

from api.models import (
    AIChatSession, Booking, Conversation, Feedback, Message, MoodNote,
    NoteAttachment, SharedNote, UserAchievement,
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
}


def _get_note_count(user):
    return MoodNote.objects.filter(user=user).count()


def _get_longest_streak(user):
    dates = list(
        MoodNote.objects.filter(user=user)
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
    """Get max character count of any note (plaintext, HTML tags stripped)."""
    from django.utils.html import strip_tags
    notes = MoodNote.objects.filter(user=user).only('encrypted_content')
    max_len = 0
    for note in notes:
        try:
            plaintext = strip_tags(note.content)
            max_len = max(max_len, len(plaintext))
        except Exception:
            pass
    return max_len


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
        MoodNote.objects.filter(user=user)
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
    """Count distinct tags across all notes."""
    tags = set()
    for meta in MoodNote.objects.filter(user=user).values_list('metadata', flat=True):
        if meta and isinstance(meta, dict):
            for tag in (meta.get('tags') or []):
                tags.add(tag)
    return len(tags)


def _get_weather_note_count(user):
    """Count notes that have a non-empty weather field."""
    count = 0
    for meta in MoodNote.objects.filter(user=user).values_list('metadata', flat=True):
        if meta and isinstance(meta, dict) and meta.get('weather'):
            count += 1
    return count


def _get_progress(user):
    """Calculate progress for all achievements. Returns dict of achievement_id -> current value."""
    note_count = _get_note_count(user)
    longest_streak = _get_longest_streak(user)
    share_count = SharedNote.objects.filter(note__user=user).count()
    booking_count = Booking.objects.filter(user=user).count()
    ai_session_count = AIChatSession.objects.filter(user=user).count()
    pinned_count = MoodNote.objects.filter(user=user, is_pinned=True).count()
    ai_analyzed = _get_ai_analyzed_count(user)
    mood_buckets = _get_distinct_mood_buckets(user)

    # Time-based: check any note written at night/early
    has_night = MoodNote.objects.filter(user=user, created_at__hour__gte=0, created_at__hour__lt=5).exists()
    has_early = MoodNote.objects.filter(user=user, created_at__hour__gte=5, created_at__hour__lt=7).exists()

    # New achievement metrics
    image_count = NoteAttachment.objects.filter(note__user=user, file_type='image').count()
    has_weekend = _has_weekend_pair(user)
    distinct_months = MoodNote.objects.filter(user=user).dates('created_at', 'month').count()
    low_stress_count = MoodNote.objects.filter(user=user, stress_index__isnull=False, stress_index__lte=3).count()

    # Emotional range: has both >0.6 and <-0.6
    has_high = MoodNote.objects.filter(user=user, sentiment_score__gt=0.6).exists()
    has_low = MoodNote.objects.filter(user=user, sentiment_score__lt=-0.6).exists()
    emotional_range = (1 if has_high else 0) + (1 if has_low else 0)

    conversation_count = Conversation.objects.filter(user=user).count()
    message_count = Message.objects.filter(sender=user).count()
    tag_count = _get_distinct_tag_count(user)
    weather_count = _get_weather_note_count(user)
    feedback_count = Feedback.objects.filter(user=user).count()

    return {
        'first_note': note_count,
        'notes_10': note_count,
        'notes_50': note_count,
        'notes_100': note_count,
        'long_writer': _get_max_note_length(user),
        'streak_3': longest_streak,
        'streak_7': longest_streak,
        'streak_30': longest_streak,
        'mood_explorer': mood_buckets,
        'positive_streak': 3 if _has_positive_streak(user) else 0,
        'mood_improver': 3 if _has_mood_improving(user) else 0,
        'self_aware': ai_analyzed,
        'first_share': share_count,
        'first_booking': booking_count,
        'first_ai_chat': ai_session_count,
        'ai_chat_10': ai_session_count,
        'night_owl': 1 if has_night else 0,
        'early_bird': 1 if has_early else 0,
        'pin_master': pinned_count,
        # New achievements
        'notes_200': note_count,
        'first_image': image_count,
        'weekend_warrior': 1 if has_weekend else 0,
        'dedicated_months_3': distinct_months,
        'stress_manager': low_stress_count,
        'emotional_range': emotional_range,
        'conversation_starter': conversation_count,
        'messages_50': message_count,
        'tag_collector': tag_count,
        'weather_logger': weather_count,
        'feedback_giver': feedback_count,
    }


def check_achievements(user):
    """Check all achievement conditions and unlock any new ones. Returns list of newly unlocked IDs."""
    existing = set(
        UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
    )
    progress = _get_progress(user)
    newly_unlocked = []

    for aid, defn in ACHIEVEMENT_DEFINITIONS.items():
        if aid in existing:
            continue
        current = progress.get(aid, 0)
        if current >= defn['threshold']:
            UserAchievement.objects.create(user=user, achievement_id=aid)
            newly_unlocked.append(aid)

    return newly_unlocked


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
