"""Install a PeriodicTask that fires send_due_habit_reminders every 15 min.

Idempotent: get_or_create on the IntervalSchedule + PeriodicTask, so re-running
the migration on a database that already has them does nothing. Backwards path
deletes the PeriodicTask but leaves the IntervalSchedule (it might be reused
by other tasks).
"""

from django.db import migrations


TASK_NAME = 'habit-reminders-every-15-min'
TASK_PATH = 'api.tasks.send_due_habit_reminders'


def install_schedule(apps, schema_editor):
    try:
        IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
        PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    except LookupError:
        # django_celery_beat not installed — nothing to do.
        return

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=15,
        period='minutes',
    )
    PeriodicTask.objects.update_or_create(
        name=TASK_NAME,
        defaults={
            'interval': schedule,
            'task': TASK_PATH,
            'enabled': True,
            'description': 'Fires habit reminder notifications when their reminder_time hits and the habit isn’t checked in today.',
        },
    )


def uninstall_schedule(apps, schema_editor):
    try:
        PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    except LookupError:
        return
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0048_habit_reminder_enabled_habit_reminder_time_and_more'),
        ('django_celery_beat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(install_schedule, uninstall_schedule),
    ]
