"""Export historical user activity into CSVs for Random Forest training.

Usage:
    python manage.py export_ml_training_data --task=mood_prediction --days=180
    python manage.py export_ml_training_data --task=stress_spike   --days=180

The output CSV captures one row per (user, day) and includes:
  * the day-aggregated MoodNote signals (avg sentiment, avg stress, count)
  * the day's DailySleep entry (if any)
  * habit completion rate for the day
  * lag features built from the previous 1/3/7/14 days
  * target columns appropriate to the task

`--task=mood_prediction`     target = sentiment_score / stress_index on day+3
`--task=stress_spike`        target = 1 if max stress in next 3 days >= 7 else 0
"""
import csv
import os
from collections import defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Max
from django.utils import timezone

from api.models import DailySleep, Habit, HabitLog, HealthMetric, JournalStreak, MoodNote

User = get_user_model()

# Lag windows (in days) used as features
LAG_WINDOWS = (1, 3, 7, 14)


class Command(BaseCommand):
    help = 'Export training data for HeartBox Random Forest models.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            choices=['mood_prediction', 'stress_spike'],
            default='mood_prediction',
            help='Which prediction task to export training data for.',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=180,
            help='How many days of history to consider (default 180).',
        )
        parser.add_argument(
            '--horizon',
            type=int,
            default=3,
            help='Forecast horizon in days for prediction targets (default 3).',
        )
        parser.add_argument(
            '--min-entries',
            type=int,
            default=7,
            help='Skip users with fewer than this many journal entries.',
        )
        parser.add_argument(
            '--output-dir',
            default='ml/datasets',
            help='Directory (relative to backend/) to write CSVs into.',
        )

    def handle(self, *args, **opts):
        task = opts['task']
        days = opts['days']
        horizon = opts['horizon']
        min_entries = opts['min_entries']
        output_dir = opts['output_dir']

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        os.makedirs(output_dir, exist_ok=True)
        outfile = os.path.join(output_dir, f'{task}_{end_date.isoformat()}.csv')

        # --- Pull per-user-day aggregates in 4 queries (no N+1) ---
        self.stdout.write(self.style.NOTICE(
            f'Exporting {task} | range={start_date}..{end_date} | horizon={horizon}d'
        ))

        notes_by_user_day = self._aggregate_notes(start_date)
        sleep_by_user_day = self._aggregate_sleep(start_date)
        habits_by_user_day = self._aggregate_habits(start_date)
        health_by_user_day = self._aggregate_health(start_date)
        streak_by_user = self._latest_streak()

        # Eligible users — at least N entries in the window
        eligible_users = {
            uid for uid, days_dict in notes_by_user_day.items()
            if sum(d['count'] for d in days_dict.values()) >= min_entries
        }
        self.stdout.write(self.style.NOTICE(
            f'Eligible users: {len(eligible_users)} (min_entries={min_entries})'
        ))

        # --- Build rows ---
        rows = []
        for uid in eligible_users:
            user_notes = notes_by_user_day.get(uid, {})
            user_sleep = sleep_by_user_day.get(uid, {})
            user_habits = habits_by_user_day.get(uid, {})

            # Sort days the user has any signal on
            all_days = sorted(set(user_notes.keys()) | set(user_sleep.keys()) | set(user_habits.keys()))

            for ref_day in all_days:
                # Need full LAG_WINDOWS[-1] history + horizon future days
                if (ref_day - start_date).days < max(LAG_WINDOWS):
                    continue
                if (end_date - ref_day).days < horizon:
                    continue

                feats = self._build_features(
                    ref_day, user_notes, user_sleep, user_habits,
                    health_by_user_day.get(uid, {}), streak_by_user.get(uid),
                )

                # Targets
                if task == 'mood_prediction':
                    target_day = ref_day + timedelta(days=horizon)
                    target_note = user_notes.get(target_day)
                    if not target_note or target_note.get('avg_sentiment') is None:
                        continue  # no ground truth on target day
                    feats['target_sentiment'] = round(target_note['avg_sentiment'], 3)
                    feats['target_stress'] = (
                        round(target_note['avg_stress'], 2) if target_note['avg_stress'] is not None else None
                    )
                else:  # stress_spike
                    future_max = 0
                    for h in range(1, horizon + 1):
                        d = ref_day + timedelta(days=h)
                        n = user_notes.get(d)
                        if n and n.get('avg_stress') is not None:
                            future_max = max(future_max, n['avg_stress'])
                    if future_max == 0:
                        continue  # no entries in horizon window
                    feats['target_spike'] = int(future_max >= 7)

                feats['user_id'] = uid
                feats['ref_date'] = ref_day.isoformat()
                rows.append(feats)

        if not rows:
            self.stdout.write(self.style.WARNING('No rows produced — too little data.'))
            return

        # Write CSV
        field_order = ['user_id', 'ref_date'] + [k for k in rows[0].keys() if k not in ('user_id', 'ref_date')]
        with open(outfile, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=field_order)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f'Wrote {len(rows)} rows -> {outfile}'))

        # Quick distribution summary
        if task == 'mood_prediction':
            sentis = [r['target_sentiment'] for r in rows if r['target_sentiment'] is not None]
            stresses = [r['target_stress'] for r in rows if r['target_stress'] is not None]
            if sentis:
                self.stdout.write(
                    f'  target_sentiment: min={min(sentis):.2f} max={max(sentis):.2f} '
                    f'mean={sum(sentis)/len(sentis):.2f} n={len(sentis)}'
                )
            if stresses:
                self.stdout.write(
                    f'  target_stress: min={min(stresses):.1f} max={max(stresses):.1f} '
                    f'mean={sum(stresses)/len(stresses):.2f} n={len(stresses)}'
                )
        else:
            pos = sum(r['target_spike'] for r in rows)
            self.stdout.write(
                f'  target_spike: positives={pos} ({pos/len(rows)*100:.1f}%) of {len(rows)}'
            )

    # ----------------------------------------------------------------------
    # Aggregation helpers (one DB query each, returning nested dicts)
    # ----------------------------------------------------------------------

    def _aggregate_notes(self, start_date):
        """{ user_id: { date: {avg_sentiment, avg_stress, count} } }"""
        out = defaultdict(dict)
        rows = (
            MoodNote.objects
            .filter(created_at__date__gte=start_date, is_deleted=False, sentiment_score__isnull=False)
            .extra(select={'day': 'DATE(created_at)'})
            .values('user_id', 'day')
            .annotate(
                avg_sentiment=Avg('sentiment_score'),
                avg_stress=Avg('stress_index'),
                count=Count('id'),
            )
        )
        for r in rows:
            out[r['user_id']][r['day']] = {
                'avg_sentiment': r['avg_sentiment'],
                'avg_stress': r['avg_stress'],
                'count': r['count'],
            }
        return out

    def _aggregate_sleep(self, start_date):
        """{ user_id: { date: {hours, quality, deep_min, light_min, rem_min, bedtime_hour} } }"""
        out = defaultdict(dict)
        rows = DailySleep.objects.filter(date__gte=start_date).values(
            'user_id', 'date', 'sleep_hours', 'sleep_quality',
            'deep_sleep_minutes', 'light_sleep_minutes', 'rem_sleep_minutes',
            'bedtime',
        )
        for r in rows:
            out[r['user_id']][r['date']] = {
                'hours': r['sleep_hours'],
                'quality': r['sleep_quality'],
                'deep_min': r['deep_sleep_minutes'],
                'light_min': r['light_sleep_minutes'],
                'rem_min': r['rem_sleep_minutes'],
                'bedtime_hour': (
                    r['bedtime'].hour + r['bedtime'].minute / 60 if r['bedtime'] else None
                ),
            }
        return out

    def _aggregate_health(self, start_date):
        """{ user_id: { date: {steps, hrv, rhr, exercise_min} } }

        HealthMetric stores one row per (user, date, metric_type) — we
        pivot to one row per (user, date) with each metric as a column.
        """
        type_map = {
            'steps': 'steps',
            'exercise_minutes': 'exercise_min',
            'hrv': 'hrv',
            'heart_rate': 'rhr',
        }
        out = defaultdict(lambda: defaultdict(dict))
        for r in HealthMetric.objects.filter(
            date__gte=start_date, metric_type__in=list(type_map.keys()),
        ).values('user_id', 'date', 'metric_type', 'value'):
            out[r['user_id']][r['date']][type_map[r['metric_type']]] = r['value']
        return {uid: dict(days) for uid, days in out.items()}

    def _aggregate_habits(self, start_date):
        """{ user_id: { date: completion_rate } } — fraction of active habits checked in."""
        out = defaultdict(dict)
        # Active habits per user
        active_per_user = defaultdict(int)
        for h in Habit.objects.filter(is_active=True).values('user_id'):
            active_per_user[h['user_id']] += 1
        # Habit logs aggregated
        rows = (
            HabitLog.objects
            .filter(date__gte=start_date)
            .values('user_id', 'date')
            .annotate(checked=Count('id', distinct=True))
        )
        for r in rows:
            total = active_per_user.get(r['user_id']) or 1
            out[r['user_id']][r['date']] = round(r['checked'] / total, 3)
        return out

    def _latest_streak(self):
        """{ user_id: current_streak } snapshot at export time."""
        return {
            s['user_id']: s['current_streak']
            for s in JournalStreak.objects.values('user_id', 'current_streak')
        }

    # ----------------------------------------------------------------------
    # Per-row feature engineering
    # ----------------------------------------------------------------------

    def _build_features(self, ref_day, user_notes, user_sleep, user_habits, user_health, current_streak):
        """Build the full v3 lag-feature dict for one (user, ref_day) row."""
        import statistics as _stats

        feats = {}
        for w in LAG_WINDOWS:
            window_days = [ref_day - timedelta(days=i) for i in range(1, w + 1)]
            # Notes
            sents, stresses, counts = [], [], 0
            for d in window_days:
                n = user_notes.get(d)
                if n:
                    if n['avg_sentiment'] is not None:
                        sents.append(n['avg_sentiment'])
                    if n['avg_stress'] is not None:
                        stresses.append(n['avg_stress'])
                    counts += n['count']
            feats[f'sent_lag_{w}d_mean'] = round(sum(sents) / len(sents), 3) if sents else 0.0
            feats[f'stress_lag_{w}d_mean'] = round(sum(stresses) / len(stresses), 2) if stresses else 0.0
            feats[f'stress_lag_{w}d_max'] = round(max(stresses), 2) if stresses else 0.0
            feats[f'entries_lag_{w}d'] = counts

            # Sleep
            sleeps = [user_sleep[d]['hours'] for d in window_days
                      if d in user_sleep and user_sleep[d].get('hours') is not None]
            feats[f'sleep_lag_{w}d_mean'] = round(sum(sleeps) / len(sleeps), 2) if sleeps else 0.0
            qualities = [user_sleep[d]['quality'] for d in window_days
                         if d in user_sleep and user_sleep[d].get('quality') is not None]
            feats[f'sleep_quality_lag_{w}d_mean'] = round(sum(qualities) / len(qualities), 2) if qualities else 0.0
            deep_pcts = []
            for d in window_days:
                s = user_sleep.get(d) or {}
                deep = s.get('deep_min') or 0
                light = s.get('light_min') or 0
                rem = s.get('rem_min') or 0
                tot = deep + light + rem
                if tot > 0:
                    deep_pcts.append(deep / tot)
            feats[f'deep_sleep_pct_lag_{w}d_mean'] = round(sum(deep_pcts) / len(deep_pcts), 3) if deep_pcts else 0.0

            # Habits
            habit_rates = [user_habits[d] for d in window_days if d in user_habits]
            feats[f'habit_lag_{w}d_mean'] = round(sum(habit_rates) / len(habit_rates), 3) if habit_rates else 0.0

            # Health metrics
            def health_field(key):
                return [user_health[d][key] for d in window_days
                        if d in user_health and user_health[d].get(key) is not None]
            steps = health_field('steps')
            exercise = health_field('exercise_min')
            hrv = health_field('hrv')
            rhr = health_field('rhr')
            feats[f'steps_lag_{w}d_mean'] = round(sum(steps) / len(steps), 0) if steps else 0.0
            feats[f'exercise_lag_{w}d_mean'] = round(sum(exercise) / len(exercise), 1) if exercise else 0.0
            feats[f'hrv_lag_{w}d_mean'] = round(sum(hrv) / len(hrv), 1) if hrv else 0.0
            feats[f'rhr_lag_{w}d_mean'] = round(sum(rhr) / len(rhr), 1) if rhr else 0.0

        # Categorical/time
        feats['day_of_week'] = ref_day.weekday()
        feats['is_weekend'] = int(ref_day.weekday() >= 5)
        feats['day_of_month'] = ref_day.day
        feats['current_streak'] = current_streak or 0

        # Bedtime consistency
        bedtime_hours = []
        for d in [ref_day - timedelta(days=i) for i in range(1, 15)]:
            s = user_sleep.get(d) or {}
            if s.get('bedtime_hour') is not None:
                bedtime_hours.append(s['bedtime_hour'])
        feats['bedtime_std_14d'] = round(_stats.stdev(bedtime_hours), 2) if len(bedtime_hours) >= 2 else 0.0

        return feats
