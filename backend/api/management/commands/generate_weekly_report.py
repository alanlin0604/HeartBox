from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate weekly summaries for all active users'

    def handle(self, *args, **options):
        from api.tasks import generate_weekly_summaries

        count = generate_weekly_summaries()
        self.stdout.write(self.style.SUCCESS(f'Generated {count} weekly summaries'))
