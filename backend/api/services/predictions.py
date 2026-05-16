"""
Mood and stress prediction service using trend analysis
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count
from ..models import MoodNote
import statistics


def calculate_trend(values):
    """
    Calculate linear trend using simple linear regression.
    Returns slope (positive = improving, negative = declining) and strength.
    """
    if len(values) < 2:
        return 0, 0

    n = len(values)
    x = list(range(n))
    y = values

    # Calculate means
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    # Calculate slope (beta)
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0, 0

    slope = numerator / denominator

    # Calculate R-squared for trend strength
    y_pred = [slope * (i - x_mean) + y_mean for i in x]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))

    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    return slope, r_squared


def get_mood_prediction(user):
    """
    Predict mood trends based on recent history.
    Returns prediction insights and warnings.
    """
    # Analyze last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__gte=thirty_days_ago
    ).order_by('created_at')

    if recent_notes.count() < 5:
        return {
            'has_prediction': False,
            'message': 'Need at least 5 journal entries in the past 30 days to generate predictions.',
            'recommendations': []
        }

    # Extract sentiment and stress data
    sentiments = list(recent_notes.values_list('sentiment_score', flat=True))
    stresses = list(recent_notes.values_list('stress_index', flat=True))

    # Remove None values
    sentiments = [s for s in sentiments if s is not None]
    stresses = [s for s in stresses if s is not None]

    if not sentiments or not stresses:
        return {
            'has_prediction': False,
            'message': 'Insufficient data for prediction.',
            'recommendations': []
        }

    # Calculate trends
    sentiment_slope, sentiment_strength = calculate_trend(sentiments)
    stress_slope, stress_strength = calculate_trend(stresses)

    # Calculate current averages
    current_sentiment = statistics.mean(sentiments[-7:] if len(sentiments) >= 7 else sentiments)
    current_stress = statistics.mean(stresses[-7:] if len(stresses) >= 7 else stresses)

    # Generate prediction
    prediction = {
        'has_prediction': True,
        'sentiment': {
            'current': round(current_sentiment, 2),
            'trend': 'improving' if sentiment_slope > 0.01 else 'declining' if sentiment_slope < -0.01 else 'stable',
            'slope': round(sentiment_slope, 3),
            'strength': round(sentiment_strength, 2),
            'forecast_7d': round(current_sentiment + (sentiment_slope * 7), 2) if abs(sentiment_slope) > 0.01 else current_sentiment,
        },
        'stress': {
            'current': round(current_stress, 1),
            'trend': 'increasing' if stress_slope > 0.05 else 'decreasing' if stress_slope < -0.05 else 'stable',
            'slope': round(stress_slope, 3),
            'strength': round(stress_strength, 2),
            'forecast_7d': round(current_stress + (stress_slope * 7), 1) if abs(stress_slope) > 0.05 else current_stress,
        },
        'warnings': [],
        'recommendations': [],
    }

    # --- Hybrid: layer Random Forest predictions on top of the trend baseline ---
    # The RF model is trained against actual 3-day-ahead outcomes, so its
    # numbers are usually more accurate than a linear extrapolation. We
    # keep the trend output as `forecast_7d` (legacy contract) and add
    # `rf_forecast_3d` so the frontend can compare both during shadow phase.
    try:
        from .ml_predictor import get_predictor
        predictor = get_predictor()
        rf_mood = predictor.predict_mood(user.id)
        if rf_mood:
            prediction['sentiment']['rf_forecast_3d'] = rf_mood['sentiment_in_3d']
            prediction['stress']['rf_forecast_3d'] = rf_mood['stress_in_3d']
            prediction['rf_model_version'] = rf_mood['model_version']
        rf_spike = predictor.predict_stress_spike(user.id)
        if rf_spike:
            prediction['stress_spike_risk'] = {
                'probability': rf_spike['spike_probability'],
                'high_risk': rf_spike['high_risk'],
                'threshold': rf_spike['threshold'],
            }
            # Surface a high-priority warning if the classifier thinks risk is high
            if rf_spike['high_risk']:
                prediction['warnings'].insert(0, {
                    'level': 'high',
                    'type': 'stress_spike_predicted',
                    'message': (
                        f'Based on your recent patterns, there is a '
                        f'{int(rf_spike["spike_probability"] * 100)}% chance of a '
                        f'high-stress day in the next 3 days. Consider preventive self-care.'
                    ),
                    'icon': '⚠️',
                })
    except Exception:
        # ML is opt-in — never let a model failure break the existing endpoint.
        import logging
        logging.getLogger(__name__).debug('RF augmentation unavailable', exc_info=True)

    # Generate warnings and recommendations
    # Warning 1: Declining mood trend
    if sentiment_slope < -0.02 and sentiment_strength > 0.3:
        prediction['warnings'].append({
            'level': 'medium' if sentiment_slope > -0.05 else 'high',
            'type': 'mood_decline',
            'message': f'Your mood has been declining over the past {recent_notes.count()} days. This is a noticeable downward trend.',
            'icon': '📉'
        })
        prediction['recommendations'].append('Consider reaching out to friends, family, or a counselor for support.')
        prediction['recommendations'].append('Engage in activities that previously brought you joy.')

    # Warning 2: Increasing stress trend
    if stress_slope > 0.05 and stress_strength > 0.3:
        prediction['warnings'].append({
            'level': 'medium' if stress_slope < 0.15 else 'high',
            'type': 'stress_increase',
            'message': f'Your stress levels are rising. Current trend suggests continued increase.',
            'icon': '⚠️'
        })
        prediction['recommendations'].append('Practice stress-reduction techniques like deep breathing or meditation.')
        prediction['recommendations'].append('Review your current commitments and consider what you might delegate or postpone.')

    # Warning 3: High current stress
    if current_stress > 7:
        prediction['warnings'].append({
            'level': 'high',
            'type': 'high_stress',
            'message': f'Your current stress level is high ({current_stress:.1f}/10). This may impact your well-being.',
            'icon': '🚨'
        })
        prediction['recommendations'].append('Prioritize rest and self-care activities.')
        prediction['recommendations'].append('Consider professional help if stress persists.')

    # Warning 4: Low current mood with declining trend
    if current_sentiment < -0.3 and sentiment_slope < 0:
        prediction['warnings'].append({
            'level': 'high',
            'type': 'mood_low_declining',
            'message': 'Your mood is low and continuing to decline. Please prioritize your mental health.',
            'icon': '💔'
        })
        prediction['recommendations'].append('Reach out to a mental health professional.')
        prediction['recommendations'].append('Talk to trusted friends or family members.')

    # Positive reinforcement
    if sentiment_slope > 0.02 and sentiment_strength > 0.3:
        prediction['warnings'].append({
            'level': 'positive',
            'type': 'mood_improving',
            'message': 'Your mood is improving! Keep up the positive momentum.',
            'icon': '📈'
        })
        prediction['recommendations'].append('Reflect on what changes or habits have helped you feel better.')
        prediction['recommendations'].append('Continue the practices that are working well for you.')

    if stress_slope < -0.05 and stress_strength > 0.3:
        prediction['warnings'].append({
            'level': 'positive',
            'type': 'stress_decreasing',
            'message': 'Your stress levels are decreasing. Well done managing your stressors!',
            'icon': '✅'
        })
        prediction['recommendations'].append('Maintain your current stress management strategies.')

    # Add general recommendations if no specific ones
    if not prediction['recommendations']:
        prediction['recommendations'] = [
            'Continue journaling regularly to track your emotional patterns.',
            'Maintain a balanced routine with sleep, exercise, and social connection.',
            'Be mindful of early warning signs and seek support when needed.',
        ]

    return prediction


def get_health_tips(user):
    """
    Generate personalized health tips based on user's patterns.
    """
    tips = []

    # Analyze recent patterns
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_notes = MoodNote.objects.filter(
        user=user,
        is_deleted=False,
        created_at__gte=seven_days_ago
    )

    if not recent_notes.exists():
        return []

    avg_stats = recent_notes.aggregate(
        avg_sentiment=Avg('sentiment_score'),
        avg_stress=Avg('stress_index')
    )

    # Tip based on stress
    if avg_stats['avg_stress'] and avg_stats['avg_stress'] > 6:
        tips.append({
            'category': 'stress',
            'tip': 'High stress detected. Try the 4-7-8 breathing technique: breathe in for 4 counts, hold for 7, exhale for 8.',
            'icon': '🫁'
        })

    # Tip based on mood
    if avg_stats['avg_sentiment'] and avg_stats['avg_sentiment'] < -0.2:
        tips.append({
            'category': 'mood',
            'tip': 'Physical activity can boost mood. Try a 10-minute walk or light stretching.',
            'icon': '🏃'
        })

    # General wellness tips
    general_tips = [
        {
            'category': 'sleep',
            'tip': 'Maintain a consistent sleep schedule. Aim for 7-9 hours per night.',
            'icon': '😴'
        },
        {
            'category': 'nutrition',
            'tip': 'Stay hydrated. Aim for 8 glasses of water daily. Dehydration can affect mood.',
            'icon': '💧'
        },
        {
            'category': 'social',
            'tip': 'Connect with others. Social support is crucial for mental well-being.',
            'icon': '👥'
        },
        {
            'category': 'mindfulness',
            'tip': 'Practice gratitude. Write down 3 things you\'re grateful for each day.',
            'icon': '🙏'
        },
    ]

    # Add 1-2 general tips
    import random
    tips.extend(random.sample(general_tips, min(2, len(general_tips))))

    return tips
