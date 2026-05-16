"""Train a Random Forest to predict sentiment + stress 3 days ahead.

Usage (from backend/):
    python -m ml.scripts.train_mood_prediction \\
        --input  ml/datasets/mood_prediction_2026-05-16.csv \\
        --output ml/models/mood_prediction_v1.joblib

The script reads the CSV produced by `manage.py export_ml_training_data`,
trains two RandomForestRegressor heads (sentiment, stress) inside a single
MultiOutputRegressor, runs 5-fold cross-validation, and serialises both the
model and the metadata needed at inference time (column order, version,
training-set stats for shadow-mode comparison).

Designed to be honest about small datasets: if you have < 50 rows it warns
loudly and uses a constant 5-fold split, but still produces a usable
artefact for the shadow phase.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

# Allow `python -m ml.scripts.train_mood_prediction` to find the project root.
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent.parent))

from ml.features import feature_columns  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='CSV produced by export_ml_training_data')
    parser.add_argument('--output', required=True, help='joblib path to write')
    parser.add_argument('--n-estimators', type=int, default=200)
    parser.add_argument('--max-depth', type=int, default=12)
    parser.add_argument('--min-samples-leaf', type=int, default=3)
    parser.add_argument('--cv-folds', type=int, default=5)
    args = parser.parse_args()

    import numpy as np
    import joblib
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold, cross_val_score
    from sklearn.multioutput import MultiOutputRegressor

    columns = feature_columns()

    # --- Load CSV ---
    X_rows: list[list[float]] = []
    y_sent: list[float] = []
    y_stress: list[float] = []
    skipped_missing_stress = 0
    with open(args.input, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('target_sentiment') in (None, ''):
                continue
            # Skip rows missing stress target — we can't train multi-output
            # without both. Honest baseline: ~40% of rows have no stress on
            # target day for users who didn't add a mood when journalling.
            if row.get('target_stress') in (None, ''):
                skipped_missing_stress += 1
                continue
            X_rows.append([float(row.get(c, 0) or 0) for c in columns])
            y_sent.append(float(row['target_sentiment']))
            y_stress.append(float(row['target_stress']))

    if not X_rows:
        print('FATAL: no usable rows after filtering — cannot train.', file=sys.stderr)
        sys.exit(1)

    X = np.array(X_rows)
    y = np.column_stack([y_sent, y_stress])
    print(f'Loaded {len(X_rows)} rows (skipped {skipped_missing_stress} for missing stress target)')

    if len(X_rows) < 50:
        warnings.warn(
            f'Only {len(X_rows)} training rows — model will be weak. '
            'Re-train against prod data when you have more entries.',
            stacklevel=1,
        )

    # --- Cross-validated baseline (MAE) ---
    base = RandomForestRegressor(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        random_state=42,
        n_jobs=-1,
    )
    model = MultiOutputRegressor(base)

    n_folds = min(args.cv_folds, max(2, len(X_rows) // 5))
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    fold_metrics = []
    for fold_idx, (tr_idx, va_idx) in enumerate(kf.split(X)):
        m = MultiOutputRegressor(RandomForestRegressor(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_leaf=args.min_samples_leaf,
            random_state=42,
            n_jobs=-1,
        ))
        m.fit(X[tr_idx], y[tr_idx])
        preds = m.predict(X[va_idx])
        fold_metrics.append({
            'fold': fold_idx,
            'sent_mae': float(mean_absolute_error(y[va_idx, 0], preds[:, 0])),
            'stress_mae': float(mean_absolute_error(y[va_idx, 1], preds[:, 1])),
            'sent_r2': float(r2_score(y[va_idx, 0], preds[:, 0])),
            'stress_r2': float(r2_score(y[va_idx, 1], preds[:, 1])),
        })

    avg = {
        k: round(sum(m[k] for m in fold_metrics) / len(fold_metrics), 3)
        for k in ('sent_mae', 'stress_mae', 'sent_r2', 'stress_r2')
    }
    print(f'CV metrics (avg over {n_folds} folds): {avg}')

    # --- Train final model on the full dataset ---
    model.fit(X, y)
    train_pred = model.predict(X)
    final_metrics = {
        'sent_mae_train': round(float(mean_absolute_error(y[:, 0], train_pred[:, 0])), 3),
        'stress_mae_train': round(float(mean_absolute_error(y[:, 1], train_pred[:, 1])), 3),
        'sent_rmse_train': round(float(np.sqrt(mean_squared_error(y[:, 0], train_pred[:, 0]))), 3),
        'stress_rmse_train': round(float(np.sqrt(mean_squared_error(y[:, 1], train_pred[:, 1]))), 3),
    }
    print(f'Final-fit metrics: {final_metrics}')

    # --- Serialise with metadata ---
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        'task': 'mood_prediction',
        'version': out_path.stem,
        'trained_at': datetime.utcnow().isoformat(),
        'n_train_rows': len(X_rows),
        'feature_columns': columns,
        'model': model,
        'cv_metrics': avg,
        'final_metrics': final_metrics,
        'targets': ['sentiment', 'stress'],
        'horizon_days': 3,
    }
    joblib.dump(bundle, out_path, compress=3)
    print(f'Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)')

    # Also write a human-readable summary
    summary_path = out_path.with_suffix('.summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'task': bundle['task'],
            'trained_at': bundle['trained_at'],
            'n_train_rows': bundle['n_train_rows'],
            'cv_metrics': bundle['cv_metrics'],
            'final_metrics': bundle['final_metrics'],
            'feature_columns': bundle['feature_columns'],
        }, f, indent=2)
    print(f'Wrote {summary_path}')


if __name__ == '__main__':
    main()
