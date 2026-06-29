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

from api.models import DailySleep, Habit, HabitLog, HealthMetric, PublicPost

User = get_user_model()

# One habit per account, profile-aligned with the diary narrative.
HABIT_DEFS = {
    'test':  {'name': '每日散步 10 分鐘', 'icon': '🚶', 'color': '#10b981',
              'category': '運動', 'completion_rate': 0.75},
    'test1': {'name': '睡前不滑手機', 'icon': '📵', 'color': '#3b82f6',
              'category': '睡眠', 'completion_rate': 0.55},
    'test2': {'name': '讀書 30 分鐘', 'icon': '📚', 'color': '#8b5cf6',
              'category': '學習', 'completion_rate': 0.82},
    'test3': {'name': '4-7-8 呼吸法練習', 'icon': '🌬️', 'color': '#f59e0b',
              'category': '正念',  'completion_rate': 0.42},
}

# One anonymous community post per account — matches the b9cac3a inline
# seeds that were lost when --reset wiped the users.
COMMUNITY_POSTS = {
    'test':  ('平淡的日子過得有意思',
              '今天沒什麼特別的事，但傍晚走回家的時候發現夕陽特別漂亮，'
              '突然覺得這種沒事的日子也挺好的。以前總覺得要有大事發生才算「過生活」，'
              '現在開始能享受這種平淡了。',
              0.5, 'happiness'),
    'test1': ('吵了一架',
              '跟交往兩年的男友吵架，氣到把自己關在房間。'
              '其實我也知道是小事，但累積太多沒講出來的不滿，'
              '一次爆發就什麼都記得很清楚。冷靜下來後又開始懷疑是不是自己太敏感了。',
              -0.5, 'stress'),
    'test2': ('讀書會跨出第一步',
              '今天終於去參加了同事邀請的讀書會。本來緊張到想取消，'
              '但去了之後發現大家都很溫暖，連我講話時手會抖都沒人介意。'
              '感覺像是把自己往前推了一點點，很值得。',
              0.6, 'happiness'),
    'test3': ('失眠快兩個月',
              '又是凌晨三點睡不著的一天。'
              '看了三個月前的日記，那時候還能一夜好眠。不知道從什麼時候開始變成這樣的，'
              '白天累到不行，晚上躺下又精神到天亮。',
              -0.6, 'anxiety'),
}

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
                # Per-day "activity mode": realistic days are not uniform —
                # 18% high-activity, 18% low/rest, 64% normal. This widens
                # the distribution enough that the dashboard's bucket-based
                # insight (needs ≥2 buckets with ≥3 samples each) can find
                # a real signal instead of dumping every day in one bucket.
                roll = rng.random()
                if roll < 0.18:
                    mode = 'high'       # active day — gym / long walk
                elif roll < 0.36:
                    mode = 'low'        # rest day
                else:
                    mode = 'normal'

                for metric_type, prof_key in METRIC_TYPES_FROM_PROFILE.items():
                    base = profile[prof_key]
                    if metric_type in ('heart_rate', 'hrv'):
                        # Physiological metrics have a tight natural range —
                        # don't push them wild even on "active days".
                        val = base * rng.uniform(0.92, 1.08)
                    elif mode == 'high':
                        val = base * rng.uniform(1.5, 2.4)
                    elif mode == 'low':
                        val = base * rng.uniform(0.30, 0.65)
                    else:  # normal
                        val = base * rng.uniform(0.75, 1.25)
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

            # --- Habit + HabitLog seed (one habit per account) ---
            habit_def = HABIT_DEFS.get(username)
            habit_logs_written = 0
            if habit_def:
                # Wipe existing habits for this user inside the window. Then
                # recreate one habit + completion logs at the configured rate.
                Habit.objects.filter(user=user).delete()  # cascades HabitLog
                habit = Habit.objects.create(
                    user=user,
                    name=habit_def['name'],
                    description='',
                    category=habit_def['category'],
                    color=habit_def['color'],
                    icon=habit_def['icon'],
                    target_frequency='daily',
                    target_count=1,
                    is_active=True,
                )
                log_rows = []
                for offset in range(days):
                    d = start_day + timedelta(days=offset)
                    if rng.random() < habit_def['completion_rate']:
                        log_rows.append(HabitLog(habit=habit, user=user, date=d))
                HabitLog.objects.bulk_create(log_rows, batch_size=200)
                habit_logs_written = len(log_rows)

            # --- PublicPost seed (one anonymous community post per account) ---
            community_written = 0
            post_def = COMMUNITY_POSTS.get(username)
            if post_def:
                # Wipe THIS user's existing public posts so reruns don't pile up.
                PublicPost.objects.filter(user=user).delete()
                _title, content, sentiment, category = post_def
                # Stagger created_at across the past 7 days so the feed
                # doesn't show all 4 posts stamped at the same second.
                stagger_days = (3 - list(PROFILES.keys()).index(username)) + 1
                PublicPost.objects.create(
                    user=user,
                    content=content,
                    sentiment_score=sentiment,
                    category=category,
                    is_active=True,
                )
                # bump created_at via update so it's slightly in the past.
                # auto_now_add prevents direct setting on .create().
                ago = timezone.now() - timedelta(days=stagger_days, hours=rng.randint(0, 18))
                PublicPost.objects.filter(user=user).update(created_at=ago)
                community_written = 1

            self.stdout.write(self.style.SUCCESS(
                f'{username}: wrote {len(sleep_rows)} sleep + {len(metric_rows)} metrics '
                f'+ {habit_logs_written} habit logs + {community_written} public post '
                f'({start_day} → {today})'
            ))
            total_sleep += len(sleep_rows)
            total_metrics += len(metric_rows)

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                f'Done. Total: {total_sleep} sleep rows + {total_metrics} health metrics.'
            ))
