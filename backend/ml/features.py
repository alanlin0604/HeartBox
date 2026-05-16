"""Shared feature definitions for HeartBox ML models.

The training pipeline (ml/scripts/train_*.py) and runtime predictor
(api/services/ml_predictor.py) MUST agree on the feature column order
and meaning. Each model bundle stores its own `feature_columns` list —
inference subsets the full feature dict down to exactly what the loaded
bundle expects, so older bundles keep working even after we add columns.

Version history:
  v2: mood + stress lags + sleep_hours + habits + time-of-week (28 cols)
  v3: + wearable health metrics (HRV, steps, exercise, resting HR,
       deep-sleep ratio, user-rated sleep quality, bedtime consistency)
       — 53 cols total
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Iterable

LAG_WINDOWS = (1, 3, 7, 14)


def feature_columns_v2() -> list[str]:
    """Original feature set — kept for backward compatibility with v2 bundles."""
    cols: list[str] = []
    for w in LAG_WINDOWS:
        cols += [
            f'sent_lag_{w}d_mean',
            f'stress_lag_{w}d_mean',
            f'stress_lag_{w}d_max',
            f'entries_lag_{w}d',
            f'sleep_lag_{w}d_mean',
            f'habit_lag_{w}d_mean',
        ]
    cols += ['day_of_week', 'is_weekend', 'day_of_month', 'current_streak']
    return cols


def feature_columns_v3() -> list[str]:
    """Expanded feature set adding wearable health data.

    HRV is the autonomic-stress gold standard; deep-sleep minutes
    correlate with next-day mood better than total sleep hours;
    bedtime variability is linked to mood disorders in research.
    """
    cols: list[str] = []
    for w in LAG_WINDOWS:
        cols += [
            f'sent_lag_{w}d_mean',
            f'stress_lag_{w}d_mean',
            f'stress_lag_{w}d_max',
            f'entries_lag_{w}d',
            f'sleep_lag_{w}d_mean',
            f'habit_lag_{w}d_mean',
            f'steps_lag_{w}d_mean',
            f'exercise_lag_{w}d_mean',
            f'hrv_lag_{w}d_mean',
            f'rhr_lag_{w}d_mean',
            f'sleep_quality_lag_{w}d_mean',
            f'deep_sleep_pct_lag_{w}d_mean',
        ]
    cols += [
        'day_of_week', 'is_weekend', 'day_of_month', 'current_streak',
        'bedtime_std_14d',  # std-dev of bedtime hour over last 14 days
    ]
    return cols


def feature_columns() -> list[str]:
    """Default (newest) schema used by export + synthetic generators."""
    return feature_columns_v3()


def _mean(xs):
    return round(statistics.mean(xs), 3) if xs else 0.0


def _max(xs, default=0.0):
    return round(max(xs), 2) if xs else default


def build_inference_features_dict(
    ref_day: date,
    user_notes: dict,
    user_sleep: dict,
    user_habits: dict,
    user_health: dict,
    current_streak: int | None,
) -> dict:
    """Build the full v3 feature dict for one (user, ref_day) row.

    `user_notes` / `user_sleep` / `user_habits` follow the export-command
    nested-dict shape.
    `user_sleep[date]` may carry: hours, quality, deep_min, light_min, rem_min, bedtime_hour.
    `user_health[date]` may carry: steps, hrv, rhr, exercise_min.

    All missing values default to 0 — Random Forest is tolerant to that
    so long as zero is semantically "no signal" (not a sentinel that the
    tree could split on as a real value). For HRV/RHR this is OK because
    real values never hit zero.
    """
    feats: dict[str, float] = {}

    for w in LAG_WINDOWS:
        window_days = [ref_day - timedelta(days=i) for i in range(1, w + 1)]

        # --- Notes-derived (sentiment, stress, entry count) ---
        sents, stresses, counts = [], [], 0
        for d in window_days:
            n = user_notes.get(d)
            if n:
                if n.get('avg_sentiment') is not None:
                    sents.append(n['avg_sentiment'])
                if n.get('avg_stress') is not None:
                    stresses.append(n['avg_stress'])
                counts += n.get('count', 0)
        feats[f'sent_lag_{w}d_mean'] = _mean(sents)
        feats[f'stress_lag_{w}d_mean'] = _mean(stresses)
        feats[f'stress_lag_{w}d_max'] = _max(stresses)
        feats[f'entries_lag_{w}d'] = counts

        # --- Sleep ---
        sleep_hours = [user_sleep[d]['hours'] for d in window_days
                       if d in user_sleep and user_sleep[d].get('hours') is not None]
        feats[f'sleep_lag_{w}d_mean'] = _mean(sleep_hours)
        sleep_quality = [user_sleep[d]['quality'] for d in window_days
                         if d in user_sleep and user_sleep[d].get('quality') is not None]
        feats[f'sleep_quality_lag_{w}d_mean'] = _mean(sleep_quality)
        deep_pcts = []
        for d in window_days:
            s = user_sleep.get(d, {})
            deep = s.get('deep_min') or 0
            light = s.get('light_min') or 0
            rem = s.get('rem_min') or 0
            total = deep + light + rem
            if total > 0:
                deep_pcts.append(deep / total)
        feats[f'deep_sleep_pct_lag_{w}d_mean'] = _mean(deep_pcts)

        # --- Habits ---
        habit_rates = [user_habits[d] for d in window_days if d in user_habits]
        feats[f'habit_lag_{w}d_mean'] = _mean(habit_rates)

        # --- Wearable health ---
        steps = [user_health[d]['steps'] for d in window_days
                 if d in user_health and user_health[d].get('steps') is not None]
        feats[f'steps_lag_{w}d_mean'] = _mean(steps)
        exercise = [user_health[d]['exercise_min'] for d in window_days
                    if d in user_health and user_health[d].get('exercise_min') is not None]
        feats[f'exercise_lag_{w}d_mean'] = _mean(exercise)
        hrv = [user_health[d]['hrv'] for d in window_days
               if d in user_health and user_health[d].get('hrv') is not None]
        feats[f'hrv_lag_{w}d_mean'] = _mean(hrv)
        rhr = [user_health[d]['rhr'] for d in window_days
               if d in user_health and user_health[d].get('rhr') is not None]
        feats[f'rhr_lag_{w}d_mean'] = _mean(rhr)

    # --- Time-of-week + streak ---
    feats['day_of_week'] = ref_day.weekday()
    feats['is_weekend'] = int(ref_day.weekday() >= 5)
    feats['day_of_month'] = ref_day.day
    feats['current_streak'] = current_streak or 0

    # --- Bedtime consistency over last 14 days ---
    bedtime_hours = []
    for d in [ref_day - timedelta(days=i) for i in range(1, 15)]:
        s = user_sleep.get(d, {})
        if s.get('bedtime_hour') is not None:
            bedtime_hours.append(s['bedtime_hour'])
    feats['bedtime_std_14d'] = (
        round(statistics.stdev(bedtime_hours), 2) if len(bedtime_hours) >= 2 else 0.0
    )

    return feats


def select_features_for_bundle(feats_dict: dict, bundle_columns: list[str]) -> list[float]:
    """Pick the columns a specific bundle was trained on. Missing keys → 0.

    Lets v2 and v3 models coexist: v2 bundles ignore the new health columns,
    v3 bundles get all 53.
    """
    return [float(feats_dict.get(c, 0) or 0) for c in bundle_columns]


# --- Back-compat wrapper for callers that haven't been updated yet -------

def build_inference_features(
    ref_day: date,
    user_notes: dict,
    user_sleep: dict,
    user_habits: dict,
    current_streak: int | None,
) -> list[float]:
    """v2-compatible wrapper. Builds the full dict with empty health data
    and returns the v2 column subset for older predictors that don't yet
    know about health features. New code should call
    `build_inference_features_dict` + `select_features_for_bundle` instead.
    """
    feats = build_inference_features_dict(
        ref_day, user_notes, user_sleep, user_habits,
        user_health={}, current_streak=current_streak,
    )
    return select_features_for_bundle(feats, feature_columns_v2())


def to_feature_row(feats_dict: dict, columns: list[str] | None = None) -> list[float]:
    """Re-order an already-built feature dict into the requested column order."""
    cols = columns or feature_columns()
    return [float(feats_dict.get(c, 0) or 0) for c in cols]


def filter_extreme_outliers(values: Iterable[float], lo_pct=1.0, hi_pct=99.0) -> tuple[float, float]:
    sorted_vals = sorted(values)
    if not sorted_vals:
        return (0.0, 0.0)
    n = len(sorted_vals)
    return (
        sorted_vals[int(n * lo_pct / 100)],
        sorted_vals[min(n - 1, int(n * hi_pct / 100))],
    )
