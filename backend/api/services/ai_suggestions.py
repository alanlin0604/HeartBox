"""
AI-powered writing suggestions and insights service
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count
from ..models import MoodNote
import random


# Writing prompts pool
WRITING_PROMPTS = [
    "What made you smile today?",
    "What challenged you today?",
    "What are you grateful for right now?",
    "What's on your mind that you haven't expressed yet?",
    "If today had a color, what would it be and why?",
    "What was the most meaningful conversation you had recently?",
    "What are you looking forward to?",
    "What did you learn about yourself today?",
    "What would you tell your past self one week ago?",
    "What energized you today? What drained you?",
    "Describe a moment when you felt fully present today.",
    "What pattern have you noticed in your thoughts lately?",
    "What boundary do you need to set or maintain?",
    "What are you avoiding that you need to address?",
    "What small win can you celebrate today?",
]


def get_writing_prompt(user):
    """
    Returns a personalized writing prompt based on user's journaling patterns.
    """
    recent_notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).order_by('-created_at')[:10]

    # Analyze recent patterns
    if not recent_notes.exists():
        # New user - give encouraging prompt
        return {
            'prompt': "Welcome! What brings you to journaling today?",
            'reason': 'first_time'
        }

    # Check if user has been journaling consistently
    days_since_last = (timezone.now().date() - recent_notes.first().created_at.date()).days

    if days_since_last > 7:
        return {
            'prompt': "It's been a while! What's been happening in your life?",
            'reason': 'returning_user'
        }

    # Get a contextual prompt
    avg_sentiment = recent_notes.aggregate(avg=Avg('sentiment_score'))['avg']

    if avg_sentiment is not None:
        if avg_sentiment < -0.3:
            # User seems stressed/negative
            prompts = [
                "What's one small thing that could make today better?",
                "What support do you need right now?",
                "What are you learning from this difficult time?",
            ]
            return {
                'prompt': random.choice(prompts),
                'reason': 'support_needed'
            }
        elif avg_sentiment > 0.3:
            # User seems positive
            prompts = [
                "What's contributing to your positive mood lately?",
                "How can you maintain this good energy?",
                "What good habits have you built recently?",
            ]
            return {
                'prompt': random.choice(prompts),
                'reason': 'positive_momentum'
            }

    # Default: random prompt
    return {
        'prompt': random.choice(WRITING_PROMPTS),
        'reason': 'random'
    }


def get_emotional_insights(user):
    """
    Analyzes user's emotional patterns and provides insights.
    Returns a list of insights based on recent journaling data.
    """
    insights = []

    # Analyze last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__gte=thirty_days_ago
    )

    if not recent_notes.exists():
        return []

    # Calculate statistics
    stats = recent_notes.aggregate(
        avg_sentiment=Avg('sentiment_score'),
        avg_stress=Avg('stress_index'),
        count=Count('id')
    )

    # Insight 1: Journaling frequency
    if stats['count'] >= 20:
        insights.append({
            'type': 'consistency',
            'message': f"You've journaled {stats['count']} times this month! Your dedication to self-reflection is impressive.",
            'icon': '🌟'
        })
    elif stats['count'] < 5:
        insights.append({
            'type': 'consistency',
            'message': "Regular journaling can help you track patterns and emotions more effectively.",
            'icon': '💡'
        })

    # Insight 2: Emotional trend
    if stats['avg_sentiment'] is not None:
        if stats['avg_sentiment'] > 0.4:
            insights.append({
                'type': 'mood_trend',
                'message': "Your overall mood has been quite positive this month. Keep nurturing what brings you joy!",
                'icon': '😊'
            })
        elif stats['avg_sentiment'] < -0.3:
            insights.append({
                'type': 'mood_trend',
                'message': "You've been experiencing some challenging emotions. Remember, it's okay to seek support when needed.",
                'icon': '🤗'
            })
        else:
            insights.append({
                'type': 'mood_trend',
                'message': "Your emotions have been balanced. This stability can be a foundation for growth.",
                'icon': '⚖️'
            })

    # Insight 3: Stress levels
    if stats['avg_stress'] is not None:
        if stats['avg_stress'] > 7:
            insights.append({
                'type': 'stress_alert',
                'message': f"Your average stress level is {stats['avg_stress']:.1f}/10. Consider stress-reduction techniques or talking to someone.",
                'icon': '⚠️'
            })
        elif stats['avg_stress'] < 4:
            insights.append({
                'type': 'stress_positive',
                'message': "Your stress levels have been manageable. Great job maintaining your well-being!",
                'icon': '✅'
            })

    # Insight 4: Emotional variability
    # Check for recent emotional volatility
    last_week = recent_notes.filter(created_at__gte=timezone.now() - timedelta(days=7))
    if last_week.count() >= 3:
        sentiments = list(last_week.values_list('sentiment_score', flat=True))
        if sentiments:
            variance = max(sentiments) - min(sentiments)
            if variance > 1.5:
                insights.append({
                    'type': 'variability',
                    'message': "Your emotions have been fluctuating recently. Identifying triggers might help you find balance.",
                    'icon': '🎢'
                })

    # Insight 5: Most used tags (if any)
    tag_counts = {}
    for note in recent_notes.prefetch_related('tags'):
        for tag in note.tags.all():
            tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1

    if tag_counts:
        top_tag = max(tag_counts.items(), key=lambda x: x[1])
        if top_tag[1] >= 5:
            insights.append({
                'type': 'themes',
                'message': f"'{top_tag[0]}' appears frequently in your entries. This seems to be an important theme for you.",
                'icon': '🏷️'
            })

    return insights


def get_reflection_questions(user):
    """
    Generates personalized reflection questions based on user's recent patterns.
    """
    questions = []

    # Analyze last 14 days
    two_weeks_ago = timezone.now() - timedelta(days=14)
    recent_notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__gte=two_weeks_ago
    )

    if not recent_notes.exists():
        # Default questions for new or returning users
        return [
            "What patterns do you notice in your daily life?",
            "What relationships are most important to you right now?",
            "What's one area of your life you'd like to improve?"
        ]

    stats = recent_notes.aggregate(
        avg_sentiment=Avg('sentiment_score'),
        avg_stress=Avg('stress_index')
    )

    # Generate contextual questions
    if stats['avg_sentiment'] is not None and stats['avg_sentiment'] < -0.2:
        questions.extend([
            "What coping strategies have worked for you in the past?",
            "Who in your life makes you feel supported?",
            "What small step could you take to improve your situation?"
        ])

    if stats['avg_stress'] is not None and stats['avg_stress'] > 6:
        questions.extend([
            "What's the main source of your stress right now?",
            "What boundaries do you need to set?",
            "How can you create more space for rest and recovery?"
        ])

    if stats['avg_sentiment'] is not None and stats['avg_sentiment'] > 0.3:
        questions.extend([
            "What habits or practices are contributing to your well-being?",
            "How can you maintain this positive momentum?",
            "What would you like to accomplish while you're feeling good?"
        ])

    # If no specific patterns, use general reflection questions
    if not questions:
        questions = [
            "What did you learn about yourself this week?",
            "What are you most proud of recently?",
            "What would make this week feel successful?",
            "What relationship needs your attention?",
            "What's one thing you're avoiding that you need to address?"
        ]

    # Return 3-5 questions
    return random.sample(questions, min(5, len(questions)))


def get_ai_suggestions(user):
    """
    Main function that returns all AI suggestions for a user.
    """
    return {
        'writing_prompt': get_writing_prompt(user),
        'insights': get_emotional_insights(user),
        'reflection_questions': get_reflection_questions(user),
        'generated_at': timezone.now().isoformat()
    }
