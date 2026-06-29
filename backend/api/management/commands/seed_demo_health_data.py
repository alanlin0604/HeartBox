"""Re-seed sleep + health-metric data for the 4 demo test accounts.

Background: ``seed_demo_test_accounts --reset`` deletes and recreates the
``test`` / ``test1`` / ``test2`` / ``test3`` Users entirely. Because every
related model is ``on_delete=CASCADE``, that wipes the per-account sleep
records and health metrics that were seeded inline (one-off Django shell)
in commits b9cac3a + 4151365. Running this command after a ``--reset`` puts
them back, idempotently.

    python manage.py seed_demo_health_data
    python manage.py seed_demo_health_data --days 60
"""

from datetime import date, datetime, time, timedelta
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from api.models import DailySleep, HealthMetric

User = get_user_model()

# Profiles per the original seed commit messages — kept here as the
# canonical source so future re-runs reproduce the same demo narrative.
PROFILES = {
    'test': {
        'sleep_mean': 7.2, 'sleep_std': 0.55, 'quality_mean': 3.5, 'quality_std': 0.5,
        'bedtime_hour': 23, 'bedtime_jitter': 60,
        'steps': 7200, 'heart_rate': 70, 'hrv': 45, 'exercise_min': 28, 'calories': 270,
        'gap_rate': 0.10,
    },
    'test1': {
        # volatile sleeper — wider sleep_std + lower quality mean
        'sleep_mean': 6.8, 'sleep_std': 1.1, 'quality_mean': 3.2, 'quality_std': 0.8,
        'bedtime_hour': 24, 'bedtime_jitter': 90,
        'steps': 6200, 'heart_rate': 74, 'hrv': 38, 'exercise_min': 20, 'calories': 220,
        'gap_rate': 0.12,
    },
    'test2': {
        # good sleeper — high mean + tight std
        'sleep_mean': 7.8, 'sleep_std': 0.4, 'quality_mean': 4.3, 'quality_std': 0.4,
        'bedtime_hour': 22, 'bedtime_jitter': 30,
        'steps': 9000, 'heart_rate': 64, 'hrv': 55, 'exercise_min': 40, 'calories': 340,
        'gap_rate': 0.08,
    },
    'test3': {
        # insomnia themes — late bedtime, low quality, low HRV
        'sleep_mean': 5.6, 'sleep_std': 1.3, 'quality_mean': 2.3, 'quality_std': 0.7,
        'bedtime_hour': 25, 'bedtime_jitter': 120,  # 25 = 01:00 next day
        'steps': 3600, 'heart_rate': 78, 'hrv': 33, 'exercise_min': 12, 'calories': 180,
        'gap_rate': 0.10,
    },
}

METRIC_TYPES_FROM_PROFILE = {
    'steps': 'steps',
    'heart_rate': 'heart_rate',
    'hrv': 'hrv',
    'active_calories': 'calories',
    'exercise_minutes': 'exercise_min',
}


def _gauss_clamp(rng, mean, std, lo, hi):
    val = rng.gauss(mean, std)
    return max(lo, min(hi, val))


class Command(BaseCommand):
    help = 'Re-seed sleep + health-metric data for test/test1/test2/test3.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=60,
                            help='Backfill window (default 60).')
        parser.add_argument('--accounts', nargs='+', default=list(PROFILES.keys()),
                            help='Subset of usernames to seed (default: all 4).')
        parser.add_argument('--seed', type=int, default=20260629,
                            help='Random seed for reproducibility.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show counts but do not write to DB.')

    def handle(self, *args, **opts):
        days = opts['days']
        accounts = opts['accounts']
        rng = random.Random(opts['seed'])
        dry = opts['dry_run']

        today = timezone.localdate()
        start_day = today - timedelta(days=days)

        total_sleep = 0
        total_metrics = 0

        for username in accounts:
            profile = PROFILES.get(username)
            if profile is None:
                self.stdout.write(self.style.WARNING(f'skip unknown profile: {username}'))
                continue
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'skip — user does not exist: {username}'))
                continue

            sleep_rows = []
            metric_rows = []

            for offset in range(days):
                d = start_day + timedelta(days=offset)
                # Per-day gap: skip both sleep + metrics together so a gap
                # day looks like a real "device not synced" day, not just a
                # metric-class outage.
                if rng.random() < profile['gap_rate']:
                    continue

                # --- DailySleep ---
                hours = _gauss_clamp(rng, profile['sleep_mean'], profile['sleep_std'], 3.0, 11.0)
                quality_raw = _gauss_clamp(rng, profile['quality_mean'], profile['quality_std'], 1.0, 5.0)
                quality = max(1, min(5, int(round(quality_raw))))

                # Bedtime: rough simulation. bedtime_hour can be >24 to mean
                # "after midnight" (e.g. 25 = 1am next day).
                bed_h = profile['bedtime_hour']
                jitter_min = rng.randint(-profile['bedtime_jitter'], profile['bedtime_jitter'])
                # bedtime is associated with the PREVIOUS evening (date d means
                # the night ending on d), so bedtime is on d - 1 day at bed_h.
                bedtime_anchor = datetime.combine(d - timedelta(days=1), time(0)) + timedelta(
                    hours=bed_h, minutes=jitter_min,
                )
                bedtime = timezone.make_aware(bedtime_anchor, timezone.get_current_timezone())
                wake_time = bedtime + timedelta(hours=hours)

                # Rough sleep-stage split — only used by the sleep insights page.
                total_minutes = int(hours * 60)
                deep = int(total_minutes * rng.uniform(0.13, 0.22))
                rem = int(total_minutes * rng.uniform(0.18, 0.28))
                light = max(0, total_minutes - deep - rem)

                sleep_rows.append(DailySleep(
                    user=user, date=d,
                    sleep_hours=round(hours, 2),
                    sleep_quality=quality,
                    bedtime=bedtime, wake_time=wake_time,
                    deep_sleep_minutes=deep,
                    light_sleep_minutes=light,
                    rem_sleep_minutes=rem,
                    source='apple_health',
                ))

                # --- HealthMetrics: 5 types per day ---
                for metric_type, prof_key in METRIC_TYPES_FROM_PROFILE.items():
                    base = profile[prof_key]
                    # Vary ±20% per day for realism
                    val = base * rng.uniform(0.8, 1.2)
                    metric_rows.append(HealthMetric(
                        user=user, date=d,
                        metric_type=metric_type,
                        value=round(val, 1),
                        source='apple_health',
                    ))

            if dry:
                self.stdout.write(self.style.NOTICE(
                    f'{username}: would write {len(sleep_rows)} sleep + {len(metric_rows)} metrics'
                ))
                continue

            # Wipe existing in window so reruns are idempotent — but ONLY in
            # the seeded date range so any real user-entered data outside the
            # window is preserved (defense-in-depth; demo accounts shouldn't
            # have any but better safe).
            DailySleep.objects.filter(
                user=user, date__gte=start_day, date__lte=today,
            ).delete()
            HealthMetric.objects.filter(
                user=user, date__gte=start_day, date__lte=today,
            ).delete()

            DailySleep.objects.bulk_create(sleep_rows, batch_size=200)
            HealthMetric.objects.bulk_create(metric_rows, batch_size=500)

            self.stdout.write(self.style.SUCCESS(
                f'{username}: wrote {len(sleep_rows)} sleep + {len(metric_rows)} metrics '
                f'({start_day} → {today})'
            ))
            total_sleep += len(sleep_rows)
            total_metrics += len(metric_rows)

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                f'Done. Total: {total_sleep} sleep rows + {total_metrics} health metrics.'
            ))
