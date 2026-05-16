"""Generate synthetic training CSVs to bootstrap the RF models.

The real prod DB has near-zero data (site not launched yet), and the dev
DB only had 16-22 rows — not enough for any useful model. This script
fabricates realistic-ish user-day time-series using patterns documented
in mood/stress psychology research:

  * Each user has a stable baseline mood + stress trait.
  * Mood is AR(1) — today's depends heavily on yesterday's.
  * Sleep negatively correlates with next-day stress (delta from 7h matters).
  * Weekends nudge mood up ~0.05.
  * Habit completion has a small positive mood effect.
  * 5% of days are "shock" events that spike stress for 2-3 days.

The output CSV matches the schema produced by
api/management/commands/export_ml_training_data.py so the existing
training scripts can consume it directly.

Usage (from backend/):
    python -m ml.scripts.generate_synthetic_data \\
        --users 200 --days 180 --task mood_prediction \\
        --output ml/datasets/mood_prediction_synthetic.csv

    python -m ml.scripts.generate_synthetic_data \\
        --users 200 --days 180 --task stress_spike \\
        --output ml/datasets/stress_spike_synthetic.csv

Output is deterministic given the same --seed.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent.parent))

from ml.features import LAG_WINDOWS, feature_columns  # noqa: E402


# -------- Per-user trait sampling ----------------------------------------

def _sample_user_traits(rng: random.Random) -> dict:
    """Trait constants for one synthetic user."""
    fitness = rng.uniform(0.3, 1.0)  # 0=sedentary, 1=athlete — drives HRV/steps/RHR
    return {
        'baseline_mood': max(-0.6, min(0.7, rng.gauss(0.15, 0.3))),
        'baseline_stress': max(0.5, min(8.0, rng.gauss(3.5, 1.8))),
        'baseline_sleep': max(4.5, min(10.0, rng.gauss(7.0, 1.2))),
        'habit_propensity': max(0.1, min(0.95, rng.gauss(0.5, 0.2))),
        'sleep_sensitivity': rng.uniform(0.04, 0.12),
        'mood_persistence': rng.uniform(0.45, 0.75),
        'stress_persistence': rng.uniform(0.5, 0.8),
        # Health traits — fitter users have higher HRV, lower RHR, more steps
        'fitness': fitness,
        'baseline_steps': max(2000, rng.gauss(6000 + fitness * 4000, 1500)),
        'baseline_hrv': max(20, rng.gauss(40 + fitness * 25, 8)),  # ms
        'baseline_rhr': max(45, rng.gauss(75 - fitness * 15, 6)),  # bpm
        'baseline_exercise_min': max(0, rng.gauss(20 + fitness * 30, 12)),
        # Bedtime regularity 0-1 — chaotic users vs. consistent sleepers
        'bedtime_regularity': rng.uniform(0.3, 1.0),
        # Only ~55% of users actually wear a watch
        'has_wearable': rng.random() < 0.55,
    }


# -------- One user's 180-day time-series ---------------------------------

def _simulate_user(traits: dict, n_days: int, start: date, rng: random.Random) -> list[dict]:
    """Returns list of per-day dicts: date, sentiment, stress, entries, sleep_hours, habit_rate."""
    days = []
    yesterday_mood = traits['baseline_mood']
    yesterday_stress = traits['baseline_stress']

    # Shock state: when triggered, adds stress for 2-3 days then decays.
    shock_remaining = 0
    shock_strength = 0

    for i in range(n_days):
        today = start + timedelta(days=i)
        # Sleep
        sleep_hours = max(3.0, min(12.0, rng.gauss(traits['baseline_sleep'], 1.0)))
        sleep_delta = sleep_hours - 7.0
        # User-rated sleep quality (1-5) correlates with hours but adds noise
        sleep_quality = max(1, min(5, round(rng.gauss(3 + sleep_delta * 0.4, 0.7))))
        # Sleep stages — deep:light:rem ≈ 1.3:4:1.7 in a typical night
        total_min = sleep_hours * 60
        deep_min = int(total_min * 0.18 + rng.gauss(0, 5))
        rem_min = int(total_min * 0.22 + rng.gauss(0, 5))
        light_min = max(0, int(total_min - deep_min - rem_min))
        deep_min = max(0, deep_min)
        rem_min = max(0, rem_min)
        # Bedtime hour — regular users cluster around their baseline (~23h)
        bedtime_hour = (22 + 2 * (1 - traits['bedtime_regularity']) * rng.gauss(0, 1)) % 24

        # Weekend effect
        is_weekend = today.weekday() >= 5
        weekend_bonus = 0.05 if is_weekend else 0.0

        # Habit completion
        monday_penalty = 0.1 if today.weekday() == 0 else 0
        habit_rate = max(0.0, min(1.0,
            rng.gauss(traits['habit_propensity'] - monday_penalty, 0.15)
        ))

        # Random shock event
        if shock_remaining == 0 and rng.random() < 0.05:
            shock_remaining = rng.randint(2, 4)
            shock_strength = rng.uniform(1.5, 3.5)
        shock_today = shock_strength if shock_remaining > 0 else 0
        if shock_remaining > 0:
            shock_remaining -= 1
            shock_strength *= 0.7

        # --- Wearable health metrics ---
        # Active days have more steps; rest days less. Weekend bonus too.
        steps_today = None
        exercise_today = None
        hrv_today = None
        rhr_today = None
        if traits['has_wearable']:
            activity_factor = rng.gauss(1.0, 0.3)
            steps_today = max(500, round(
                traits['baseline_steps'] * activity_factor * (1.1 if is_weekend else 1.0)
            ))
            exercise_today = max(0, round(
                rng.gauss(traits['baseline_exercise_min'], 12)
            ))
            # HRV drops with poor sleep + stress; recovers with exercise
            hrv_today = round(max(15,
                traits['baseline_hrv']
                - 0.6 * max(0, -sleep_delta)
                - 0.4 * yesterday_stress
                + 0.05 * exercise_today
                + rng.gauss(0, 4)
            ), 1)
            # Resting HR rises with stress + poor sleep
            rhr_today = round(max(40,
                traits['baseline_rhr']
                + 0.5 * yesterday_stress
                + 0.3 * max(0, -sleep_delta)
                + rng.gauss(0, 2)
            ), 1)

        # --- Mood = AR(1) + sleep effect + weekend + habit + exercise - shock ---
        exercise_bonus = 0.04 * (exercise_today or 0) / 30  # small mood boost from exercise
        hrv_bonus = 0.02 * ((hrv_today or 45) - 45) / 10  # higher HRV → better mood
        mood_today = (
            traits['mood_persistence'] * yesterday_mood
            + (1 - traits['mood_persistence']) * traits['baseline_mood']
            + traits['sleep_sensitivity'] * sleep_delta
            + 0.04 * (sleep_quality - 3)  # quality matters too
            + weekend_bonus
            + 0.08 * (habit_rate - 0.5)
            + exercise_bonus
            + hrv_bonus
            - 0.12 * shock_today
            + rng.gauss(0, 0.18)
        )
        mood_today = max(-1.0, min(1.0, mood_today))

        # Stress = AR(1) - mood + shock - exercise + noise
        stress_today = (
            traits['stress_persistence'] * yesterday_stress
            + (1 - traits['stress_persistence']) * traits['baseline_stress']
            - 1.2 * mood_today
            + 0.9 * shock_today
            - 0.3 * (sleep_delta if sleep_delta > 0 else 0)
            - 0.02 * (exercise_today or 0)
            + rng.gauss(0, 0.8)
        )
        stress_today = max(0.0, min(10.0, stress_today))

        if rng.random() < 0.7:
            entries = 1 if rng.random() < 0.85 else rng.randint(2, 3)
        else:
            entries = 0
            mood_today = None
            stress_today = None

        days.append({
            'date': today,
            'sentiment': round(mood_today, 3) if mood_today is not None else None,
            'stress': round(stress_today, 2) if stress_today is not None else None,
            'entries': entries,
            'sleep_hours': round(sleep_hours, 2),
            'sleep_quality': sleep_quality,
            'deep_min': deep_min,
            'light_min': light_min,
            'rem_min': rem_min,
            'bedtime_hour': round(bedtime_hour, 2),
            'habit_rate': round(habit_rate, 3),
            'steps': steps_today,
            'exercise_min': exercise_today,
            'hrv': hrv_today,
            'rhr': rhr_today,
        })

        # Roll forward (None handling: keep last known if today has no entry)
        if mood_today is not None:
            yesterday_mood = mood_today
        if stress_today is not None:
            yesterday_stress = stress_today

    return days


# -------- Lag-window feature builder (mirrors features.py) ---------------

def _mean(xs, ndigits=3):
    return round(sum(xs) / len(xs), ndigits) if xs else 0.0


def _build_row(ref_idx: int, user_days: list[dict], current_streak: int) -> dict:
    import statistics as _stats
    ref_day = user_days[ref_idx]['date']
    feats = {}
    for w in LAG_WINDOWS:
        window = user_days[max(0, ref_idx - w):ref_idx]
        sents = [d['sentiment'] for d in window if d['sentiment'] is not None]
        stresses = [d['stress'] for d in window if d['stress'] is not None]
        entries = sum(d['entries'] for d in window)
        sleeps = [d['sleep_hours'] for d in window if d['sleep_hours'] is not None]
        habits = [d['habit_rate'] for d in window if d['habit_rate'] is not None]
        # Health lags
        steps = [d['steps'] for d in window if d.get('steps') is not None]
        exercise = [d['exercise_min'] for d in window if d.get('exercise_min') is not None]
        hrvs = [d['hrv'] for d in window if d.get('hrv') is not None]
        rhrs = [d['rhr'] for d in window if d.get('rhr') is not None]
        qualities = [d['sleep_quality'] for d in window if d.get('sleep_quality') is not None]
        deep_pcts = []
        for d in window:
            deep = d.get('deep_min') or 0
            light = d.get('light_min') or 0
            rem = d.get('rem_min') or 0
            tot = deep + light + rem
            if tot > 0:
                deep_pcts.append(deep / tot)

        feats[f'sent_lag_{w}d_mean'] = _mean(sents)
        feats[f'stress_lag_{w}d_mean'] = _mean(stresses, 2)
        feats[f'stress_lag_{w}d_max'] = round(max(stresses), 2) if stresses else 0.0
        feats[f'entries_lag_{w}d'] = entries
        feats[f'sleep_lag_{w}d_mean'] = _mean(sleeps, 2)
        feats[f'habit_lag_{w}d_mean'] = _mean(habits)
        feats[f'steps_lag_{w}d_mean'] = _mean(steps, 0)
        feats[f'exercise_lag_{w}d_mean'] = _mean(exercise, 1)
        feats[f'hrv_lag_{w}d_mean'] = _mean(hrvs, 1)
        feats[f'rhr_lag_{w}d_mean'] = _mean(rhrs, 1)
        feats[f'sleep_quality_lag_{w}d_mean'] = _mean(qualities, 2)
        feats[f'deep_sleep_pct_lag_{w}d_mean'] = _mean(deep_pcts)

    feats['day_of_week'] = ref_day.weekday()
    feats['is_weekend'] = int(ref_day.weekday() >= 5)
    feats['day_of_month'] = ref_day.day
    feats['current_streak'] = current_streak
    # Bedtime variability over last 14 days
    bedtime_window = user_days[max(0, ref_idx - 14):ref_idx]
    bedtimes = [d['bedtime_hour'] for d in bedtime_window if d.get('bedtime_hour') is not None]
    feats['bedtime_std_14d'] = round(_stats.stdev(bedtimes), 2) if len(bedtimes) >= 2 else 0.0
    return feats


def _streak_at(user_days: list[dict], idx: int) -> int:
    """Count consecutive trailing days with entries."""
    streak = 0
    for j in range(idx, -1, -1):
        if user_days[j]['entries'] > 0:
            streak += 1
        else:
            break
    return streak


# -------- Main -----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--users', type=int, default=200)
    parser.add_argument('--days', type=int, default=180)
    parser.add_argument('--horizon', type=int, default=3)
    parser.add_argument('--task', choices=['mood_prediction', 'stress_spike'], required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    end = date.today()
    start = end - timedelta(days=args.days)

    print(f'Generating {args.users} users × {args.days} days | task={args.task} | seed={args.seed}')

    columns = feature_columns()
    target_cols = ['target_sentiment', 'target_stress'] if args.task == 'mood_prediction' else ['target_spike']
    field_order = ['user_id', 'ref_date'] + columns + target_cols

    rows = []
    for uid in range(1, args.users + 1):
        user_rng = random.Random(args.seed * 1000 + uid)
        traits = _sample_user_traits(user_rng)
        days = _simulate_user(traits, args.days, start, user_rng)

        max_lag = max(LAG_WINDOWS)
        for ref_idx in range(max_lag, len(days) - args.horizon):
            # Mood prediction needs target day to have an entry
            target_idx = ref_idx + args.horizon
            target_day = days[target_idx]

            feats = _build_row(ref_idx, days, _streak_at(days, ref_idx))

            if args.task == 'mood_prediction':
                if target_day['sentiment'] is None or target_day['stress'] is None:
                    continue
                feats['target_sentiment'] = target_day['sentiment']
                feats['target_stress'] = target_day['stress']
            else:  # stress_spike
                future_window = days[ref_idx + 1:ref_idx + 1 + args.horizon]
                future_stress = [d['stress'] for d in future_window if d['stress'] is not None]
                if not future_stress:
                    continue
                feats['target_spike'] = int(max(future_stress) >= 7)

            feats['user_id'] = uid
            feats['ref_date'] = days[ref_idx]['date'].isoformat()
            rows.append(feats)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=field_order)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {len(rows)} rows -> {out_path}')

    # Distribution summary
    if args.task == 'mood_prediction':
        sentis = [r['target_sentiment'] for r in rows]
        stresses = [r['target_stress'] for r in rows]
        print(
            f'  target_sentiment: min={min(sentis):.2f} max={max(sentis):.2f} '
            f'mean={sum(sentis)/len(sentis):.2f} std~{_std(sentis):.2f}'
        )
        print(
            f'  target_stress: min={min(stresses):.1f} max={max(stresses):.1f} '
            f'mean={sum(stresses)/len(stresses):.2f}'
        )
    else:
        pos = sum(r['target_spike'] for r in rows)
        print(f'  target_spike positives: {pos} ({pos/len(rows)*100:.1f}%) of {len(rows)}')


def _std(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5


if __name__ == '__main__':
    main()
