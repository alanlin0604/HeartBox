import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_weekly_summaries(self):
    """Generate weekly summaries for all active users. Scheduled every Monday.

    bind=True + retry: external aggregations + notification creates can fail
    transiently (DB blip, OpenAI throttle). Retry once after 5 min, then
    twice more. After 3 attempts we give up and surface the error to logs.

    Connection hygiene: with `.iterator()` over a potentially large user
    set on Cloud Run + Neon's pgbouncer, we can outlast the connection's
    idle timeout. Periodically close-if-unusable so Django re-opens fresh
    rather than throwing OperationalError mid-loop.
    """
    import zoneinfo
    from datetime import datetime, time
    from django.contrib.auth import get_user_model
    from django.db import connection
    from api.models import MoodNote, Notification, WeeklySummary

    User = get_user_model()

    users = User.objects.filter(is_active=True)
    created_count = 0
    processed = 0

    from django.db.models import Avg
    from api.models import NotificationPreference

    def user_local_week(user_tz_name):
        """Return (week_start_date, prev_week_start_date, prev_week_end_date,
        prev_week_start_utc, prev_week_end_utc) for the user's timezone."""
        tz = zoneinfo.ZoneInfo(user_tz_name or 'Asia/Taipei')
        local_today = datetime.now(tz).date()
        week_start = local_today - timedelta(days=local_today.weekday())
        pws = week_start - timedelta(days=7)
        pwe = week_start - timedelta(days=1)
        # UTC bounds for the previous-week window so the SQL query is tz-correct
        # regardless of which tz Django has activated at the moment.
        start_utc = datetime.combine(pws, time.min).replace(tzinfo=tz)
        end_utc = datetime.combine(pwe, time.max).replace(tzinfo=tz)
        return pws, start_utc, end_utc

    try:
        for user in users.iterator():
            # Refresh connection every 50 users to dodge idle-timeout drops.
            if processed and processed % 50 == 0:
                connection.close_if_unusable_or_obsolete()
            processed += 1

            prev_week_start, start_utc, end_utc = user_local_week(user.timezone)

            if WeeklySummary.objects.filter(user=user, week_start=prev_week_start).exists():
                continue

            notes = MoodNote.objects.filter(
                user=user,
                is_deleted=False,
                created_at__gte=start_utc,
                created_at__lte=end_utc,
            )
            note_count = notes.count()
            if note_count == 0:
                continue

            aggs = notes.aggregate(
                mood_avg=Avg('sentiment_score'),
                stress_avg=Avg('stress_index'),
            )

            tag_counts = {}
            for meta in notes.values_list('metadata', flat=True):
                for tag in (meta or {}).get('tags', []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            top_activities = sorted(tag_counts, key=tag_counts.get, reverse=True)[:5]

            WeeklySummary.objects.create(
                user=user,
                week_start=prev_week_start,
                mood_avg=aggs['mood_avg'],
                stress_avg=aggs['stress_avg'],
                note_count=note_count,
                top_activities=top_activities,
            )

            pref = NotificationPreference.objects.filter(
                user=user, notification_type='weekly_report',
            ).first()
            if not pref or pref.enabled:
                Notification.objects.create(
                    user=user,
                    type='system',
                    title='Weekly Summary Ready',
                    message=f'Your weekly summary for {prev_week_start} is ready.',
                )

            created_count += 1
    except Exception as exc:
        logger.exception('generate_weekly_summaries failed at user %s, retrying', processed)
        # Retry the whole task — created_count rows already committed will be
        # skipped on next attempt by the WeeklySummary.exists() guard above.
        raise self.retry(exc=exc)

    logger.info('Generated %d weekly summaries', created_count)
    return created_count


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def send_due_habit_reminders(self):
    """Fire reminders for habits whose reminder_time falls in the last 15 min
    (in the user's local timezone) and that haven't been checked in today.

    Runs every 15 minutes via django_celery_beat. Idempotent: if a reminder
    was already created within the last 23 hours we skip — avoids re-firing
    when the schedule overlaps the boundary.

    Each fire creates an in-app Notification AND attempts a web-push (best
    effort; push errors are swallowed since the in-app record is the
    durable signal).
    """
    import zoneinfo
    from datetime import timedelta
    from django.utils import timezone as dj_tz

    from api.models import Habit, HabitLog, Notification
    from api.views import send_push_notification

    WINDOW_SECONDS = 15 * 60   # we run every 15 min, fire if reminder hit in last 15 min
    DEDUP_HOURS = 23           # one reminder per habit per day

    now_utc = dj_tz.now()
    fired = 0

    qs = (
        Habit.objects
        .filter(reminder_enabled=True, is_active=True)
        .exclude(reminder_time__isnull=True)
        .select_related('user')
    )
    for habit in qs:
        try:
            tz_name = habit.user.timezone or 'Asia/Taipei'
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = zoneinfo.ZoneInfo('Asia/Taipei')

        now_local = now_utc.astimezone(tz)
        rt = habit.reminder_time
        target = now_local.replace(
            hour=rt.hour, minute=rt.minute, second=0, microsecond=0,
        )
        delta = (now_local - target).total_seconds()
        if not (0 <= delta < WINDOW_SECONDS):
            continue

        # Already checked in today (in user's timezone)?
        if HabitLog.objects.filter(habit=habit, date=now_local.date()).exists():
            continue

        # Already reminded recently?
        recent_cutoff = now_utc - timedelta(hours=DEDUP_HOURS)
        already = Notification.objects.filter(
            user=habit.user,
            type='habit_reminder',
            data__habit_id=habit.id,
            created_at__gte=recent_cutoff,
        ).exists()
        if already:
            continue

        Notification.objects.create(
            user=habit.user,
            type='habit_reminder',
            title=f'⏰ {habit.name}',
            message='今天還沒打卡 — 動起來！',
            data={'habit_id': habit.id, 'kind': 'reminder'},
        )
        try:
            send_push_notification(
                habit.user,
                f'⏰ {habit.name}',
                '今天還沒打卡 — 動起來！',
                url='/habits',
            )
        except Exception as e:
            logger.warning('Habit reminder push failed for habit %d: %s', habit.id, e)
        fired += 1

    if fired:
        logger.info('send_due_habit_reminders fired %d reminders', fired)
    return fired


@shared_task(bind=True)
def import_notes_task(self, job_id):
    """Process a stored CSV/JSON file for an ImportJob, updating progress and
    error fields on the model so ImportJobStatusView can poll. Designed to be
    safe under CELERY_TASK_ALWAYS_EAGER (local dev) and a real worker (prod).
    """
    import os

    from django.conf import settings
    from django.core.cache import cache
    from django.utils import timezone as tz

    from api.models import ImportJob
    from api.services.import_service import ingest_rows, parse_file

    try:
        job = ImportJob.objects.get(pk=job_id)
    except ImportJob.DoesNotExist:
        logger.warning('ImportJob %d not found', job_id)
        return

    job.status = 'running'
    job.started_at = tz.now()
    job.save(update_fields=['status', 'started_at'])

    storage_path = os.path.join(settings.MEDIA_ROOT, job.storage_key)
    try:
        with open(storage_path, 'rb') as fh:
            blob = fh.read()
        _fmt, _cols, rows = parse_file(job.filename, blob)
        job.total_rows = len(rows)
        job.save(update_fields=['total_rows'])

        # Throttle progress updates: every 25 rows or 1 second, whichever first.
        last_save_at = [tz.now()]
        last_save_n = [0]

        def progress_cb(processed, total):
            now = tz.now()
            if (processed - last_save_n[0]) >= 25 or (now - last_save_at[0]).total_seconds() >= 1.0:
                ImportJob.objects.filter(pk=job.pk).update(processed_rows=processed)
                last_save_n[0] = processed
                last_save_at[0] = now

        created, errors = ingest_rows(
            job.user, rows, mapping=job.mapping or None, progress_cb=progress_cb,
        )
        job.processed_rows = job.total_rows
        job.imported_count = created
        job.errors = errors[:50]
        job.status = 'done'
        job.completed_at = tz.now()
        job.save()

        # Invalidate analytics caches so charts pick up the new notes.
        if created > 0:
            uid = job.user_id
            now = tz.now()
            cache.delete_many([
                f'analytics_{uid}_week_30',
                f'analytics_{uid}_month_30',
                f'analytics_{uid}_week_7',
                f'calendar_{uid}_{now.year}_{now.month}',
            ])
    except Exception as e:
        logger.exception('Import job %d failed', job_id)
        job.status = 'failed'
        job.error_message = f'{e.__class__.__name__}: {e}'
        job.completed_at = tz.now()
        job.save(update_fields=['status', 'error_message', 'completed_at'])
    finally:
        # Best-effort cleanup of the staged file.
        try:
            if storage_path and os.path.exists(storage_path):
                os.remove(storage_path)
        except OSError:
            logger.warning('Could not remove staged import file %s', storage_path)
