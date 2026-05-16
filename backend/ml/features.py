"""Shared feature definitions for HeartBox ML models.

The training pipeline (ml/scripts/train_*.py) and runtime predictor
(api/services/ml_predictor.py) MUST agree on the feature column order
and meaning. Keep all of that here so a model trained yesterday can be
loaded by today's predictor.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

# Must match the lag windows used in
# api/management/commands/export_ml_training_data.py
LAG_WINDOWS = (1, 3, 7, 14)


def feature_columns() -> list[str]:
    """The full ordered feature list. Both training and inference rely on
    this order — append-only, never reorder, or stored models break.
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
        ]
    cols += ['day_of_week', 'is_weekend', 'day_of_month', 'current_streak']
    return cols


def build_inference_features(
    ref_day: date,
    user_notes: dict,
    user_sleep: dict,
    user_habits: dict,
    current_streak: int | None,
) -> list[float]:
    """Inference-time feature builder. Returns a list in `feature_columns()` order.

    `user_notes` etc. follow the same nested-dict shape used by the export
    command — see its `_aggregate_*` helpers for details.
    """
    feats: dict[str, float] = {}
    for w in LAG_WINDOWS:
        window_days = [ref_day - timedelta(days=i) for i in range(1, w + 1)]
        sents, stresses, counts = [], [], 0
        for d in window_days:
            n = user_notes.get(d)
            if n:
                if n.get('avg_sentiment') is not None:
                    sents.append(n['avg_sentiment'])
                if n.get('avg_stress') is not None:
                    stresses.append(n['avg_stress'])
                counts += n.get('count', 0)
        feats[f'sent_lag_{w}d_mean'] = round(sum(sents) / len(sents), 3) if sents else 0.0
        feats[f'stress_lag_{w}d_mean'] = round(sum(stresses) / len(stresses), 2) if stresses else 0.0
        feats[f'stress_lag_{w}d_max'] = round(max(stresses), 2) if stresses else 0.0
        feats[f'entries_lag_{w}d'] = counts

        sleep_hours = [user_sleep[d]['hours'] for d in window_days
                       if d in user_sleep and user_sleep[d].get('hours') is not None]
        feats[f'sleep_lag_{w}d_mean'] = round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else 0.0

        habit_rates = [user_habits[d] for d in window_days if d in user_habits]
        feats[f'habit_lag_{w}d_mean'] = round(sum(habit_rates) / len(habit_rates), 3) if habit_rates else 0.0

    feats['day_of_week'] = ref_day.weekday()
    feats['is_weekend'] = int(ref_day.weekday() >= 5)
    feats['day_of_month'] = ref_day.day
    feats['current_streak'] = current_streak or 0

    return [feats[c] for c in feature_columns()]


def to_feature_row(feats_dict: dict) -> list[float]:
    """Re-order an already-built feature dict (from the export CSV) into the canonical column order."""
    return [feats_dict[c] for c in feature_columns()]


def filter_extreme_outliers(values: Iterable[float], lo_pct=1.0, hi_pct=99.0) -> tuple[float, float]:
    """Helper for capping at training time. Returns (lo, hi) thresholds.

    Random Forest is fairly outlier-robust but extreme typos (e.g., stress
    accidentally entered as 100) will still hurt; we cap rather than drop.
    """
    sorted_vals = sorted(values)
    if not sorted_vals:
        return (0.0, 0.0)
    n = len(sorted_vals)
    return (
        sorted_vals[int(n * lo_pct / 100)],
        sorted_vals[min(n - 1, int(n * hi_pct / 100))],
    )
