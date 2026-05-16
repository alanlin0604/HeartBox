"""Runtime Random Forest predictor for HeartBox.

Two tasks supported today:
  * mood_prediction — regression head producing 3-day-ahead sentiment + stress
  * stress_spike    — classifier producing "stress_index ≥ 7 in next 3 days" probability

Design:
  * Singleton — one set of model bundles loaded per process.
  * Lazy-loaded on first call to keep cold-start cheap when ML is unused.
  * If a bundle is missing on disk we silently fall back to a rule-based
    estimator (the existing trend logic in services/predictions.py),
    so the API never returns an error just because a model file was
    forgotten in a deploy.
  * Inference takes < 50 ms per user (one DB round-trip to assemble
    features + one in-memory predict call).
"""
from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db.models import Avg, Count
from django.utils import timezone

logger = logging.getLogger(__name__)

# Paths are relative to BASE_DIR (backend/) — overridable by env for tests.
DEFAULT_MODEL_DIR = os.path.join(
    getattr(settings, 'BASE_DIR', '.'),
    'ml',
    'models',
)


class MLPredictor:
    """Singleton holding both RF model bundles."""

    _instance: Optional['MLPredictor'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._mood_bundle = None
                    obj._spike_bundle = None
                    obj._load_attempted = False
                    cls._instance = obj
        return cls._instance

    # ------------------------------------------------------------------
    # Bundle loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        model_dir = os.getenv('HEARTBOX_ML_MODEL_DIR', DEFAULT_MODEL_DIR)
        try:
            import joblib  # noqa: F401 — fail fast if sklearn deps missing
        except ImportError:
            logger.warning('joblib not installed; RF predictor disabled.')
            return

        mood_path = self._find_latest(model_dir, prefix='mood_prediction_v')
        if mood_path:
            try:
                self._mood_bundle = self._load_bundle(mood_path)
                logger.info('Loaded mood RF: %s', mood_path)
            except Exception as e:
                logger.warning('Failed to load mood RF (%s): %s', mood_path, e)

        spike_path = self._find_latest(model_dir, prefix='stress_spike_v')
        if spike_path:
            try:
                self._spike_bundle = self._load_bundle(spike_path)
                logger.info('Loaded spike RF: %s', spike_path)
            except Exception as e:
                logger.warning('Failed to load spike RF (%s): %s', spike_path, e)

    @staticmethod
    def _find_latest(model_dir: str, prefix: str) -> Optional[str]:
        if not os.path.isdir(model_dir):
            return None
        candidates = sorted(
            (f for f in os.listdir(model_dir) if f.startswith(prefix) and f.endswith('.joblib')),
            reverse=True,
        )
        if not candidates:
            return None
        return os.path.join(model_dir, candidates[0])

    @staticmethod
    def _load_bundle(path: str) -> dict:
        import joblib
        bundle = joblib.load(path)
        # Sanity check
        for k in ('model', 'feature_columns', 'task'):
            if k not in bundle:
                raise ValueError(f'Model bundle at {path} missing key {k}')
        return bundle

    # ------------------------------------------------------------------
    # Feature assembly (mirrors export_ml_training_data._aggregate_*)
    # ------------------------------------------------------------------

    def _assemble_user_history(self, user_id: int, ref_day):
        """Build per-day rollups for notes, sleep, habits, and health.

        Returns (notes, sleep, habits, health, streak) where each is a
        date-keyed dict matching the shape build_inference_features_dict expects.
        """
        from ..models import DailySleep, Habit, HabitLog, HealthMetric, JournalStreak, MoodNote
        from ml.features import LAG_WINDOWS

        history_start = ref_day - timedelta(days=max(LAG_WINDOWS) + 1)

        # --- Notes ---
        notes = defaultdict(lambda: {'avg_sentiment': None, 'avg_stress': None, 'count': 0})
        for r in (
            MoodNote.objects
            .filter(user_id=user_id, is_deleted=False, created_at__date__gte=history_start,
                    sentiment_score__isnull=False)
            .extra(select={'day': 'DATE(created_at)'})
            .values('day')
            .annotate(
                avg_sentiment=Avg('sentiment_score'),
                avg_stress=Avg('stress_index'),
                count=Count('id'),
            )
        ):
            notes[r['day']] = {
                'avg_sentiment': r['avg_sentiment'],
                'avg_stress': r['avg_stress'],
                'count': r['count'],
            }

        # --- Sleep (with stages + quality + bedtime hour) ---
        sleep = {}
        for s in DailySleep.objects.filter(user_id=user_id, date__gte=history_start).values(
            'date', 'sleep_hours', 'sleep_quality',
            'deep_sleep_minutes', 'light_sleep_minutes', 'rem_sleep_minutes',
            'bedtime',
        ):
            sleep[s['date']] = {
                'hours': s['sleep_hours'],
                'quality': s['sleep_quality'],
                'deep_min': s['deep_sleep_minutes'],
                'light_min': s['light_sleep_minutes'],
                'rem_min': s['rem_sleep_minutes'],
                'bedtime_hour': s['bedtime'].hour + s['bedtime'].minute / 60 if s['bedtime'] else None,
            }

        # --- Habits ---
        active_count = Habit.objects.filter(user_id=user_id, is_active=True).count() or 1
        habits = {}
        for r in (
            HabitLog.objects
            .filter(user_id=user_id, date__gte=history_start)
            .values('date')
            .annotate(checked=Count('id', distinct=True))
        ):
            habits[r['date']] = round(r['checked'] / active_count, 3)

        # --- Wearable health metrics (pivot long-form into per-day dict) ---
        health = defaultdict(dict)
        # Map model metric_type → feature key used in features.build_inference_features_dict
        type_map = {
            'steps': 'steps',
            'exercise_minutes': 'exercise_min',
            'hrv': 'hrv',
            'heart_rate': 'rhr',  # treating heart_rate as resting HR proxy
        }
        for r in (
            HealthMetric.objects
            .filter(user_id=user_id, date__gte=history_start,
                    metric_type__in=list(type_map.keys()))
            .values('date', 'metric_type', 'value')
        ):
            key = type_map.get(r['metric_type'])
            if key:
                health[r['date']][key] = r['value']

        streak = JournalStreak.objects.filter(user_id=user_id).values_list('current_streak', flat=True).first() or 0
        return notes, sleep, habits, dict(health), streak

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _features_for_bundle(self, user_id: int, bundle: dict) -> Optional[list[float]]:
        """Assemble the per-user feature vector matching exactly the columns
        the given bundle was trained on (v2 vs v3 may differ)."""
        from ml.features import build_inference_features_dict, select_features_for_bundle

        ref_day = timezone.now().date()
        notes, sleep, habits, health, streak = self._assemble_user_history(user_id, ref_day)
        feats_dict = build_inference_features_dict(
            ref_day, notes, sleep, habits, health, streak
        )
        return select_features_for_bundle(feats_dict, bundle['feature_columns'])

    def predict_mood(self, user_id: int) -> Optional[dict]:
        """Predicted sentiment + stress 3 days out, or None if no model loaded."""
        self._ensure_loaded()
        if self._mood_bundle is None:
            return None
        try:
            feats = self._features_for_bundle(user_id, self._mood_bundle)
            preds = self._mood_bundle['model'].predict([feats])[0]
            return {
                'sentiment_in_3d': round(float(preds[0]), 3),
                'stress_in_3d': round(float(preds[1]), 2),
                'model_version': self._mood_bundle.get('version', 'unknown'),
            }
        except Exception as e:
            logger.warning('mood prediction failed for user %d: %s', user_id, e)
            return None

    def predict_stress_spike(self, user_id: int) -> Optional[dict]:
        """Probability of stress >= 7 day in the next 3 days, or None."""
        self._ensure_loaded()
        if self._spike_bundle is None:
            return None
        try:
            feats = self._features_for_bundle(user_id, self._spike_bundle)
            proba = self._spike_bundle['model'].predict_proba([feats])[0]
            spike_prob = float(proba[1]) if len(proba) > 1 else 0.0
            threshold = float(self._spike_bundle.get('threshold', 0.5))
            return {
                'spike_probability': round(spike_prob, 3),
                'high_risk': spike_prob >= threshold,
                'threshold': threshold,
                'model_version': self._spike_bundle.get('version', 'unknown'),
            }
        except Exception as e:
            logger.warning('spike prediction failed for user %d: %s', user_id, e)
            return None

    # Surfaces metadata for the Admin "ML monitoring" tab
    def model_status(self) -> dict:
        self._ensure_loaded()
        def bundle_info(b):
            if not b:
                return {'loaded': False}
            return {
                'loaded': True,
                'version': b.get('version'),
                'trained_at': b.get('trained_at'),
                'n_train_rows': b.get('n_train_rows'),
                'cv_metrics': b.get('cv_metrics'),
            }
        return {
            'mood_prediction': bundle_info(self._mood_bundle),
            'stress_spike': bundle_info(self._spike_bundle),
        }


# Module-level helpers — easier to mock in tests
def get_predictor() -> MLPredictor:
    return MLPredictor()
