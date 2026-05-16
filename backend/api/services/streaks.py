from datetime import timedelta
from django.utils import timezone
from ..models import JournalStreak, MoodNote


def update_streak(user):
    """
    Update user's journaling streak based on their note history.
    Called after a new note is created.
    """
    streak, created = JournalStreak.objects.get_or_create(user=user)

    today = timezone.localdate()

    # Count total entries
    total = MoodNote.objects.filter(user=user, is_deleted=False).count()
    streak.total_entries = total

    # Get last entry date
    last_note = MoodNote.objects.filter(
        user=user, is_deleted=False
    ).order_by('-created_at').first()

    if not last_note:
        streak.current_streak = 0
        streak.last_entry_date = None
        streak.save()
        return streak

    last_date = last_note.created_at.date() if hasattr(last_note.created_at, 'date') else last_note.created_at
    streak.last_entry_date = last_date

    # Calculate current streak
    if last_date == today:
        # Entry made today — count backwards, optionally bridging missed
        # days with freeze tokens. A missing day burns one token; once
        # tokens are exhausted the streak ends. This keeps the user from
        # losing a 30-day run because of one bad day, without making the
        # streak meaningless (cap defaults to 2 tokens).
        current_streak = 1
        check_date = today - timedelta(days=1)
        freeze_budget = streak.freeze_tokens
        freeze_used = 0

        while current_streak <= 365:
            has_entry = MoodNote.objects.filter(
                user=user,
                is_deleted=False,
                created_at__date=check_date
            ).exists()

            if has_entry:
                current_streak += 1
                check_date -= timedelta(days=1)
                continue
            if freeze_used < freeze_budget:
                freeze_used += 1
                check_date -= timedelta(days=1)
                continue
            break

        if freeze_used:
            streak.freeze_tokens = max(0, streak.freeze_tokens - freeze_used)
        streak.current_streak = current_streak
    elif last_date == today - timedelta(days=1):
        # Entry made yesterday — streak continues with its prior value.
        streak.current_streak = max(streak.current_streak, 1)
    else:
        # Older than yesterday and no entry today — streak ends.
        streak.current_streak = 0

    # Update longest streak
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.save()
    return streak


def refill_freeze_tokens(user):
    """Top up the user's freeze tokens at most once per calendar month.

    Capped at JournalStreak.FREEZE_TOKEN_CAP. Called by the monthly
    Celery beat (see tasks.py:refill_streak_freeze_tokens) so the user
    accumulates a small buffer over time but can't stockpile indefinitely.
    """
    try:
        streak = JournalStreak.objects.get(user=user)
    except JournalStreak.DoesNotExist:
        return
    today = timezone.localdate()
    if streak.freeze_tokens_refilled_at and streak.freeze_tokens_refilled_at.month == today.month \
            and streak.freeze_tokens_refilled_at.year == today.year:
        return  # already refilled this month
    streak.freeze_tokens = min(streak.freeze_tokens + 1, streak.FREEZE_TOKEN_CAP)
    streak.freeze_tokens_refilled_at = today
    streak.save(update_fields=['freeze_tokens', 'freeze_tokens_refilled_at'])


def get_streak_milestone(streak_count):
    """
    Get milestone achievement for a given streak count.
    Returns None if no milestone reached.
    """
    milestones = {
        3: {'id': 'streak_3', 'nameKey': 'streak.milestone3', 'icon': '🔥'},
        7: {'id': 'streak_7', 'nameKey': 'streak.milestone7', 'icon': '⭐'},
        14: {'id': 'streak_14', 'nameKey': 'streak.milestone14', 'icon': '💪'},
        30: {'id': 'streak_30', 'nameKey': 'streak.milestone30', 'icon': '🏆'},
        60: {'id': 'streak_60', 'nameKey': 'streak.milestone60', 'icon': '🎯'},
        100: {'id': 'streak_100', 'nameKey': 'streak.milestone100', 'icon': '👑'},
        365: {'id': 'streak_365', 'nameKey': 'streak.milestone365', 'icon': '🌟'},
    }

    return milestones.get(streak_count)
