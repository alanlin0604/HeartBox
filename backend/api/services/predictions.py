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
    #
    # Horizon note: the Random Forest model is trained on a 3-day-ahead target
    # (see ml/models/*_v3.summary.json, horizon_days=3). The trend baseline
    # below now also extrapolates 3 days so the displayed number lines up with
    # both the RF prediction and the labels on the dashboard
    # ("3 天後預測" / "3-Day Forecast"). The legacy 7-day field is kept as
    # ``forecast_7d`` for any older clients still calling the API contract.
    prediction = {
        'has_prediction': True,
        'sentiment': {
            'current': round(current_sentiment, 2),
            'trend': 'improving' if sentiment_slope > 0.01 else 'declining' if sentiment_slope < -0.01 else 'stable',
            'slope': round(sentiment_slope, 3),
            'strength': round(sentiment_strength, 2),
            'forecast_3d': round(current_sentiment + (sentiment_slope * 3), 2) if abs(sentiment_slope) > 0.01 else current_sentiment,
            'forecast_7d': round(current_sentiment + (sentiment_slope * 7), 2) if abs(sentiment_slope) > 0.01 else current_sentiment,
        },
        'stress': {
            'current': round(current_stress, 1),
            'trend': 'increasing' if stress_slope > 0.05 else 'decreasing' if stress_slope < -0.05 else 'stable',
            'slope': round(stress_slope, 3),
            'strength': round(stress_strength, 2),
            'forecast_3d': round(current_stress + (stress_slope * 3), 1) if abs(stress_slope) > 0.05 else current_stress,
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
            # Surface a high-priority warning if the classifier thinks risk is high.
            # `type` doubles as the i18n key suffix on the frontend
            # (see prediction.warning.* in locales). `params` carries values
            # the localised string interpolates; clients on stale builds can
            # fall back to the English `message` string for backward compat.
            if rf_spike['high_risk']:
                percent = int(rf_spike['spike_probability'] * 100)
                prediction['warnings'].insert(0, {
                    'level': 'high',
                    'type': 'stress_spike_predicted',
                    'params': {'percent': percent},
                    'message': (
                        f'Based on your recent patterns, there is a '
                        f'{percent}% chance of a high-stress day in the next 3 days. '
                        f'Consider preventive self-care.'
                    ),
                    'icon': '⚠️',
                })
    except Exception:
        # ML is opt-in — never let a model failure break the existing endpoint.
        import logging
        logging.getLogger(__name__).debug('RF augmentation unavailable', exc_info=True)

    # Generate warnings and recommendations.
    # Convention: `type` is the i18n key suffix on the frontend; `params` is
    # the interpolation dict; `message` is a final-fallback English string
    # for older clients that don't know the type yet. Recommendations are
    # plain string IDs (frontend renders t(`prediction.rec.${id}`)).
    note_count = recent_notes.count()

    # Warning 1: Declining mood trend
    if sentiment_slope < -0.02 and sentiment_strength > 0.3:
        prediction['warnings'].append({
            'level': 'medium' if sentiment_slope > -0.05 else 'high',
            'type': 'mood_decline',
            'params': {'days': note_count},
            'message': f'Your mood has been declining over the past {note_count} days. This is a noticeable downward trend.',
            'icon': '📉',
        })
        prediction['recommendations'].append('reach_out')
        prediction['recommendations'].append('joy_activities')

    # Warning 2: Increasing stress trend
    if stress_slope > 0.05 and stress_strength > 0.3:
        prediction['warnings'].append({
            'level': 'medium' if stress_slope < 0.15 else 'high',
            'type': 'stress_increase',
            'params': {},
            'message': 'Your stress levels are rising. Current trend suggests continued increase.',
            'icon': '⚠️',
        })
        prediction['recommendations'].append('deep_breathing')
        prediction['recommendations'].append('review_commitments')

    # Warning 3: High current stress
    if current_stress > 7:
        prediction['warnings'].append({
            'level': 'high',
            'type': 'high_stress',
            'params': {'level': round(current_stress, 1)},
            'message': f'Your current stress level is high ({current_stress:.1f}/10). This may impact your well-being.',
            'icon': '🚨',
        })
        prediction['recommendations'].append('rest_self_care')
        prediction['recommendations'].append('professional_help')

    # Warning 4: Low current mood with declining trend
    if current_sentiment < -0.3 and sentiment_slope < 0:
        prediction['warnings'].append({
            'level': 'high',
            'type': 'mood_low_declining',
            'params': {},
            'message': 'Your mood is low and continuing to decline. Please prioritize your mental health.',
            'icon': '💔',
        })
        prediction['recommendations'].append('mental_health_pro')
        prediction['recommendations'].append('talk_friends')

    # Positive reinforcement
    if sentiment_slope > 0.02 and sentiment_strength > 0.3:
        prediction['warnings'].append({
            'level': 'positive',
            'type': 'mood_improving',
            'params': {},
            'message': 'Your mood is improving! Keep up the positive momentum.',
            'icon': '📈',
        })
        prediction['recommendations'].append('reflect_habits')
        prediction['recommendations'].append('continue_practices')

    if stress_slope < -0.05 and stress_strength > 0.3:
        prediction['warnings'].append({
            'level': 'positive',
            'type': 'stress_decreasing',
            'params': {},
            'message': 'Your stress levels are decreasing. Well done managing your stressors!',
            'icon': '✅',
        })
        prediction['recommendations'].append('maintain_strategies')

    # Add general recommendations if no specific ones
    if not prediction['recommendations']:
        prediction['recommendations'] = [
            'continue_journaling',
            'balanced_routine',
            'mindful_warning_signs',
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

    # Tip based on stress.
    # `tip_key` is the i18n key suffix on the frontend
    # (renders as t(`prediction.tip.${tip_key}`)). `tip` stays as an English
    # fallback for older clients that haven't picked up the new keys yet.
    if avg_stats['avg_stress'] and avg_stats['avg_stress'] > 6:
        tips.append({
            'category': 'stress',
            'tip_key': 'breathing_4_7_8',
            'tip': 'High stress detected. Try the 4-7-8 breathing technique: breathe in for 4 counts, hold for 7, exhale for 8.',
            'icon': '🫁',
        })

    # Tip based on mood
    if avg_stats['avg_sentiment'] and avg_stats['avg_sentiment'] < -0.2:
        tips.append({
            'category': 'mood',
            'tip_key': 'physical_activity',
            'tip': 'Physical activity can boost mood. Try a 10-minute walk or light stretching.',
            'icon': '🏃',
        })

    # General wellness tips
    general_tips = [
        {
            'category': 'sleep',
            'tip_key': 'consistent_sleep',
            'tip': 'Maintain a consistent sleep schedule. Aim for 7-9 hours per night.',
            'icon': '😴',
        },
        {
            'category': 'nutrition',
            'tip_key': 'hydration',
            'tip': 'Stay hydrated. Aim for 8 glasses of water daily. Dehydration can affect mood.',
            'icon': '💧',
        },
        {
            'category': 'social',
            'tip_key': 'social_connection',
            'tip': 'Connect with others. Social support is crucial for mental well-being.',
            'icon': '👥',
        },
        {
            'category': 'mindfulness',
            'tip_key': 'gratitude',
            'tip': 'Practice gratitude. Write down 3 things you\'re grateful for each day.',
            'icon': '🙏',
        },
    ]

    # Add 1-2 general tips
    import random
    tips.extend(random.sample(general_tips, min(2, len(general_tips))))

    return tips
