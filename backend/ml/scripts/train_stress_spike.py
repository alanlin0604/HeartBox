"""Train a Random Forest classifier predicting "stress >= 7 in next 3 days".

Usage (from backend/):
    python -m ml.scripts.train_stress_spike \\
        --input  ml/datasets/stress_spike_2026-05-16.csv \\
        --output ml/models/stress_spike_v1.joblib

Output bundle includes the model, columns, AUC + precision/recall per fold,
and the operating threshold suggested by Youden's J on the validation folds.
The runtime predictor uses that threshold to map probability → "high risk".
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent.parent))

from ml.features import feature_columns  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--n-estimators', type=int, default=300)
    parser.add_argument('--max-depth', type=int, default=10)
    parser.add_argument('--min-samples-leaf', type=int, default=2)
    parser.add_argument('--cv-folds', type=int, default=5)
    args = parser.parse_args()

    import numpy as np
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        average_precision_score, precision_score, recall_score, f1_score,
        roc_auc_score, roc_curve,
    )
    from sklearn.model_selection import StratifiedKFold

    columns = feature_columns()

    X_rows, y_rows = [], []
    with open(args.input, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('target_spike') in (None, ''):
                continue
            X_rows.append([float(row.get(c, 0) or 0) for c in columns])
            y_rows.append(int(row['target_spike']))

    if not X_rows:
        print('FATAL: no usable rows after filtering.', file=sys.stderr)
        sys.exit(1)

    X = np.array(X_rows)
    y = np.array(y_rows)
    pos_rate = float(y.mean())
    print(f'Loaded {len(X_rows)} rows | positive rate {pos_rate * 100:.1f}%')

    if pos_rate < 0.05 or pos_rate > 0.95:
        warnings.warn(
            f'Severely imbalanced positive class ({pos_rate*100:.1f}%) — '
            'model will likely default to the majority class. Augment data.',
            stacklevel=1,
        )

    if len(X_rows) < 50:
        warnings.warn(
            f'Only {len(X_rows)} training rows — model will be weak. '
            'Re-train against prod data when you have more.',
            stacklevel=1,
        )

    # --- Stratified k-fold CV ---
    n_folds = min(args.cv_folds, max(2, sum(y == 1), sum(y == 0)))
    # `class_weight=balanced` partially compensates for imbalance — for very
    # rare positives we may still need explicit SMOTE in a follow-up.
    base_kwargs = dict(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
    )

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    fold_metrics = []
    best_thresholds = []
    for fold_idx, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
        clf = RandomForestClassifier(**base_kwargs)
        clf.fit(X[tr_idx], y[tr_idx])
        proba = clf.predict_proba(X[va_idx])[:, 1]
        try:
            auc = float(roc_auc_score(y[va_idx], proba))
            ap = float(average_precision_score(y[va_idx], proba))
        except ValueError:
            auc, ap = float('nan'), float('nan')
        # Youden's J statistic for best threshold
        try:
            fpr, tpr, thr = roc_curve(y[va_idx], proba)
            j = tpr - fpr
            best_t = float(thr[j.argmax()])
        except ValueError:
            best_t = 0.5
        preds_at_t = (proba >= best_t).astype(int)
        fold_metrics.append({
            'fold': fold_idx,
            'auc': auc,
            'avg_precision': ap,
            'precision_at_t': float(precision_score(y[va_idx], preds_at_t, zero_division=0)),
            'recall_at_t': float(recall_score(y[va_idx], preds_at_t, zero_division=0)),
            'f1_at_t': float(f1_score(y[va_idx], preds_at_t, zero_division=0)),
            'best_threshold': best_t,
        })
        best_thresholds.append(best_t)

    def avg(key):
        vals = [m[key] for m in fold_metrics if m[key] == m[key]]  # filter NaN
        return round(sum(vals) / len(vals), 3) if vals else None

    summary = {k: avg(k) for k in ('auc', 'avg_precision', 'precision_at_t', 'recall_at_t', 'f1_at_t')}
    # Filter out infs/NaNs from folds with no positives — they produce
    # `inf` thresholds that would render the model useless at inference.
    valid_thresholds = [t for t in best_thresholds if t not in (float('inf'), float('nan')) and t == t]
    chosen_threshold = round(sum(valid_thresholds) / len(valid_thresholds), 3) if valid_thresholds else 0.5
    print(f'CV metrics: {summary} | chosen_threshold={chosen_threshold}')

    # Final fit
    clf = RandomForestClassifier(**base_kwargs)
    clf.fit(X, y)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        'task': 'stress_spike',
        'version': out_path.stem,
        'trained_at': datetime.utcnow().isoformat(),
        'n_train_rows': len(X_rows),
        'positive_rate': round(pos_rate, 3),
        'feature_columns': columns,
        'model': clf,
        'threshold': chosen_threshold,
        'cv_metrics': summary,
        'horizon_days': 3,
        'spike_threshold': 7,
    }
    joblib.dump(bundle, out_path, compress=3)
    print(f'Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)')

    summary_path = out_path.with_suffix('.summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({k: bundle[k] for k in bundle if k != 'model'}, f, indent=2, default=str)
    print(f'Wrote {summary_path}')


if __name__ == '__main__':
    main()
