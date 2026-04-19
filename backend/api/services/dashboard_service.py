"""
Dashboard service for managing dashboard layouts and widget data.
"""
from datetime import timedelta
from django.db.models import Avg, Count, Q
from django.utils import timezone

from ..models import (
    MoodNote, JournalStreak, Habit, HabitLog,
    DailySleep, HealthMetric, AIChatSession
)


def get_default_layout():
    """Return the default dashboard layout configuration."""
    return {
        "widgets": [
            {"id": "streak", "x": 0, "y": 0, "w": 4, "h": 2, "enabled": True},
            {"id": "mood_trends", "x": 4, "y": 0, "w": 8, "h": 4, "enabled": True},
            {"id": "on_this_day", "x": 0, "y": 2, "w": 4, "h": 3, "enabled": True},
            {"id": "habit_checkin", "x": 4, "y": 4, "w": 4, "h": 3, "enabled": True},
            {"id": "ai_suggestions", "x": 8, "y": 4, "w": 4, "h": 3, "enabled": True},
            {"id": "sleep_stats", "x": 0, "y": 5, "w": 4, "h": 2, "enabled": False},
        ]
    }


def get_widget_data(user, widget_id):
    """
    Fetch data for a specific widget.

    Args:
        user: User instance
        widget_id: Widget identifier string

    Returns:
        dict: Widget-specific data
    """
    widget_handlers = {
        'streak': _get_streak_data,
        'mood_trends': _get_mood_trends_data,
        'on_this_day': _get_on_this_day_data,
        'habit_checkin': _get_habit_checkin_data,
        'ai_suggestions': _get_ai_suggestions_data,
        'sleep_stats': _get_sleep_stats_data,
    }

    handler = widget_handlers.get(widget_id)
    if not handler:
        return {"error": f"Unknown widget_id: {widget_id}"}

    return handler(user)


def _get_streak_data(user):
    """Get journaling streak data."""
    try:
        streak = JournalStreak.objects.get(user=user)
        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "total_entries": streak.total_entries,
        }
    except JournalStreak.DoesNotExist:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_entries": 0,
        }


def _get_mood_trends_data(user):
    """Get mood trends for the last 7 days."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=6)  # Last 7 days including today

    # Get notes for the last 7 days
    notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        sentiment_score__isnull=False
    ).values('created_at__date').annotate(
        avg_sentiment=Avg('sentiment_score')
    ).order_by('created_at__date')

    # Create a dict for quick lookup
    notes_dict = {
        note['created_at__date']: note['avg_sentiment']
        for note in notes
    }

    # Generate data for all 7 days
    dates = []
    mood_scores = []

    for i in range(7):
        date = start_date + timedelta(days=i)
        dates.append(date.isoformat())
        # Convert sentiment (-1 to 1) to mood score (0 to 10)
        sentiment = notes_dict.get(date)
        if sentiment is not None:
            mood_score = round((sentiment + 1) * 5, 1)  # Convert to 0-10 scale
            mood_scores.append(mood_score)
        else:
            mood_scores.append(None)

    # Calculate average mood (excluding None values)
    valid_scores = [s for s in mood_scores if s is not None]
    avg_mood = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

    return {
        "dates": dates,
        "mood_scores": mood_scores,
        "avg_mood": avg_mood,
    }


def _get_on_this_day_data(user):
    """Get notes from previous years on this day."""
    today = timezone.now().date()

    # Get notes from the same month and day in previous years
    notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__month=today.month,
        created_at__day=today.day,
    ).exclude(
        created_at__year=today.year  # Exclude current year
    ).order_by('-created_at')[:5]

    memories = []
    for note in notes:
        memories.append({
            "id": note.id,
            "date": note.created_at.date().isoformat(),
            "year": note.created_at.year,
            "preview": note.content_preview,
            "sentiment_score": note.sentiment_score,
        })

    return {
        "memories": memories,
        "count": len(memories),
    }


def _get_habit_checkin_data(user):
    """Get today's habit check-in status."""
    today = timezone.now().date()

    # Get active habits
    habits = Habit.objects.filter(user=user, is_active=True)

    habit_data = []
    for habit in habits:
        # Check if completed today
        completed = HabitLog.objects.filter(
            habit=habit,
            date=today
        ).exists()

        # Calculate current streak
        current_streak = _calculate_habit_streak(habit)

        habit_data.append({
            "id": habit.id,
            "name": habit.name,
            "color": habit.color,
            "icon": habit.icon,
            "completed": completed,
            "current_streak": current_streak,
        })

    completed_count = sum(1 for h in habit_data if h['completed'])
    total_count = len(habit_data)

    return {
        "habits": habit_data,
        "completed_count": completed_count,
        "total_count": total_count,
        "completion_rate": round((completed_count / total_count * 100), 1) if total_count > 0 else 0,
    }


def _calculate_habit_streak(habit):
    """Calculate current streak for a habit."""
    today = timezone.now().date()

    # Check if completed today
    if not HabitLog.objects.filter(habit=habit, date=today).exists():
        return 0

    streak = 1
    check_date = today - timedelta(days=1)

    # Count backwards
    while HabitLog.objects.filter(habit=habit, date=check_date).exists():
        streak += 1
        check_date -= timedelta(days=1)

        # Safety limit
        if streak > 365:
            break

    return streak


def _get_ai_suggestions_data(user):
    """Get AI-generated suggestions based on recent activity."""
    # Check if user has recent chat sessions
    recent_session = AIChatSession.objects.filter(
        user=user,
        is_active=True
    ).order_by('-updated_at').first()

    # Get recent mood trends
    last_7_days = timezone.now().date() - timedelta(days=7)
    recent_notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__date__gte=last_7_days
    )

    avg_sentiment = recent_notes.aggregate(
        avg_sentiment=Avg('sentiment_score')
    )['avg_sentiment']

    avg_stress = recent_notes.aggregate(
        avg_stress=Avg('stress_index')
    )['avg_stress']

    # Generate simple suggestions based on patterns
    suggestions = []

    if avg_sentiment is not None and avg_sentiment < -0.3:
        suggestions.append({
            "type": "mood",
            "title": "Low mood detected",
            "message": "Your recent entries show lower mood. Consider trying mindfulness exercises.",
            "action": "view_courses",
        })

    if avg_stress is not None and avg_stress > 7:
        suggestions.append({
            "type": "stress",
            "title": "High stress levels",
            "message": "You've been experiencing high stress. Try breathing exercises or meditation.",
            "action": "wellness_sessions",
        })

    # Check journal streak
    try:
        streak = JournalStreak.objects.get(user=user)
        if streak.current_streak == 0 and streak.total_entries > 0:
            suggestions.append({
                "type": "streak",
                "title": "Keep your streak going",
                "message": "Start a new journaling streak today!",
                "action": "create_note",
            })
    except JournalStreak.DoesNotExist:
        pass

    return {
        "suggestions": suggestions[:3],  # Return max 3 suggestions
        "count": len(suggestions),
    }


def _get_sleep_stats_data(user):
    """Get sleep statistics for the last 7 days."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=6)

    sleep_records = DailySleep.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')

    dates = []
    hours = []
    quality = []

    for record in sleep_records:
        dates.append(record.date.isoformat())
        hours.append(round(record.sleep_hours, 1))
        quality.append(record.sleep_quality)

    # Calculate averages
    avg_hours = round(sum(hours) / len(hours), 1) if hours else None
    avg_quality = round(sum(quality) / len(quality), 1) if quality else None

    return {
        "dates": dates,
        "hours": hours,
        "quality": quality,
        "avg_hours": avg_hours,
        "avg_quality": avg_quality,
        "record_count": len(dates),
    }


def update_metric_current_value(user, metric_type):
    """
    Update the current value for a specific metric type.
    This can be called periodically or after relevant user actions.

    Args:
        user: User instance
        metric_type: Type of metric to update

    Returns:
        float: Updated current value
    """
    calculators = {
        'daily_entries': _calculate_daily_entries,
        'avg_mood': _calculate_avg_mood,
        'streak_days': _calculate_streak_days,
        'habit_completion': _calculate_habit_completion,
        'sleep_hours': _calculate_sleep_hours,
        'exercise_minutes': _calculate_exercise_minutes,
    }

    calculator = calculators.get(metric_type)
    if not calculator:
        return 0.0

    return calculator(user)


def _calculate_daily_entries(user):
    """Calculate number of journal entries in the last 7 days."""
    last_7_days = timezone.now().date() - timedelta(days=7)
    count = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__date__gte=last_7_days
    ).count()
    return float(count)


def _calculate_avg_mood(user):
    """Calculate average mood score for the last 7 days (0-10 scale)."""
    last_7_days = timezone.now().date() - timedelta(days=7)
    avg_sentiment = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__date__gte=last_7_days,
        sentiment_score__isnull=False
    ).aggregate(avg=Avg('sentiment_score'))['avg']

    if avg_sentiment is None:
        return 0.0

    # Convert sentiment (-1 to 1) to mood score (0 to 10)
    return round((avg_sentiment + 1) * 5, 1)


def _calculate_streak_days(user):
    """Get current journaling streak."""
    try:
        streak = JournalStreak.objects.get(user=user)
        return float(streak.current_streak)
    except JournalStreak.DoesNotExist:
        return 0.0


def _calculate_habit_completion(user):
    """Calculate habit completion rate for the last 7 days (percentage)."""
    last_7_days = timezone.now().date() - timedelta(days=7)

    active_habits_count = Habit.objects.filter(user=user, is_active=True).count()
    if active_habits_count == 0:
        return 0.0

    total_expected = active_habits_count * 7
    completed_logs = HabitLog.objects.filter(
        user=user,
        date__gte=last_7_days
    ).count()

    return round((completed_logs / total_expected) * 100, 1) if total_expected > 0 else 0.0


def _calculate_sleep_hours(user):
    """Calculate average sleep hours for the last 7 days."""
    last_7_days = timezone.now().date() - timedelta(days=7)
    avg_sleep = DailySleep.objects.filter(
        user=user,
        date__gte=last_7_days
    ).aggregate(avg=Avg('sleep_hours'))['avg']

    return round(avg_sleep, 1) if avg_sleep else 0.0


def _calculate_exercise_minutes(user):
    """Calculate average exercise minutes for the last 7 days."""
    last_7_days = timezone.now().date() - timedelta(days=7)
    avg_exercise = HealthMetric.objects.filter(
        user=user,
        metric_type='exercise_minutes',
        date__gte=last_7_days
    ).aggregate(avg=Avg('value'))['avg']

    return round(avg_exercise, 1) if avg_exercise else 0.0
