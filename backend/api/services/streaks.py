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
        # Entry made today - count backwards
        current_streak = 1
        check_date = today - timedelta(days=1)

        while True:
            has_entry = MoodNote.objects.filter(
                user=user,
                is_deleted=False,
                created_at__date=check_date
            ).exists()

            if not has_entry:
                break

            current_streak += 1
            check_date -= timedelta(days=1)

            # Safety limit
            if current_streak > 365:
                break

        streak.current_streak = current_streak
    elif last_date == today - timedelta(days=1):
        # Entry made yesterday - streak continues
        streak.current_streak = max(streak.current_streak, 1)
    else:
        # Streak broken
        streak.current_streak = 0

    # Update longest streak
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.save()
    return streak


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
