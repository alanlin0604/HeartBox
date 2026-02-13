from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Delete all users except root (CASCADE deletes related data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm execution (required to actually delete)',
        )

    def handle(self, *args, **options):
        users_to_delete = User.objects.exclude(username='root')
        count = users_to_delete.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No users to delete (only root exists).'))
            return

        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                f'Found {count} user(s) to delete (all except root).\n'
                f'Run with --confirm to execute deletion.'
            ))
            return

        deleted_count, deleted_details = users_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} user(s) and {deleted_count} total objects:'))
        for model, cnt in deleted_details.items():
            self.stdout.write(f'  {model}: {cnt}')
