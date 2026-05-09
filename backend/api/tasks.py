import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, subject, message, from_email, recipient_list):
    """Send email asynchronously via Celery."""
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception as exc:
        logger.warning('Email send failed, retrying: %s', exc)
        self.retry(exc=exc)


@shared_task
def generate_weekly_summaries():
    """Generate weekly summaries for all active users. Scheduled every Monday."""
    from django.contrib.auth import get_user_model
    from api.models import MoodNote, Notification, WeeklySummary

    User = get_user_model()
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday of this week
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)

    users = User.objects.filter(is_active=True)
    created_count = 0

    for user in users.iterator():
        # Skip if summary already exists
        if WeeklySummary.objects.filter(user=user, week_start=prev_week_start).exists():
            continue

        notes = MoodNote.objects.filter(
            user=user,
            is_deleted=False,
            created_at__date__gte=prev_week_start,
            created_at__date__lte=prev_week_end,
        )

        note_count = notes.count()
        if note_count == 0:
            continue

        from django.db.models import Avg
        aggs = notes.aggregate(
            mood_avg=Avg('sentiment_score'),
            stress_avg=Avg('stress_index'),
        )

        # Collect top activities from metadata
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

        # Create notification (respecting user preferences)
        from api.models import NotificationPreference
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

    logger.info('Generated %d weekly summaries', created_count)
    return created_count


@shared_task
def send_push_notification_task(user_id, title, body, url='/'):
    """Send push notification asynchronously."""
    from api.views import send_push_notification
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        send_push_notification(user, title, body, url)
    except User.DoesNotExist:
        logger.warning('User %d not found for push notification', user_id)


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
