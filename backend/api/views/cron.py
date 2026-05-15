"""HTTP cron endpoints invoked by an external scheduler (Cloud Scheduler).

Cloud Run scales to zero and we don't run a Celery beat process, so we let
an external scheduler poke us every N minutes/days. Each endpoint validates
a shared secret and runs the underlying task synchronously, returning a
small JSON summary so the scheduler logs surface what happened.

Setup:
1. Set ``CRON_SECRET`` env var on the Cloud Run service (a long random string).
2. Create a Cloud Scheduler job per endpoint with HTTP POST + header
   ``X-Cron-Secret: <same value>``.

Plain Django views (not DRF) so they don't show up in the OpenAPI schema —
these are infrastructure plumbing, not part of the public API surface.
"""
import hmac
import logging
import os

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _check_secret(request):
    expected = os.getenv('CRON_SECRET')
    if not expected:
        # Refuse rather than letting anonymous traffic in if env is missing.
        logger.error('CRON_SECRET is not set; refusing cron request')
        return False
    provided = request.headers.get('X-Cron-Secret') or ''
    return hmac.compare_digest(provided, expected)


@csrf_exempt
@require_POST
def run_habit_reminders(request):
    """POST /api/internal/cron/habit-reminders/ — fire 15-min habit reminders."""
    if not _check_secret(request):
        return JsonResponse({'detail': 'forbidden'}, status=403)
    from api.tasks import send_due_habit_reminders
    fired = send_due_habit_reminders()
    return JsonResponse({'fired': fired})


@csrf_exempt
@require_POST
def run_weekly_summaries(request):
    """POST /api/internal/cron/weekly-summaries/ — generate previous-week summaries.

    Schedule weekly (e.g. Monday 06:00 in user-local-ish timezone). Idempotent
    via ``WeeklySummary.objects.filter(...).exists()`` guard inside the task.
    """
    if not _check_secret(request):
        return JsonResponse({'detail': 'forbidden'}, status=403)
    from api.tasks import generate_weekly_summaries
    created = generate_weekly_summaries()
    return JsonResponse({'created': created})
