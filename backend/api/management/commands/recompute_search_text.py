"""One-off migration: recompute MoodNote.search_text using the new
proportional formula (30% of length, capped 200, floor 20).

The old formula stored the first 500 chars verbatim, which meant any
note under 500 chars was 100% plaintext in the DB. The new formula
limits the plaintext footprint to ~30% of the note's actual length,
so short notes leak proportionally less.

This command:
  - Walks every MoodNote (including soft-deleted ones)
  - Decrypts the content via the existing encryption_service
  - Re-truncates via MoodNote._make_search_text
  - UPDATEs only the search_text column (encrypted_content untouched)

Safe to re-run: idempotent. Skips rows already truncated under the new
rule.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils.html import strip_tags

from api.models import MoodNote


class Command(BaseCommand):
    help = 'Recompute MoodNote.search_text using the new proportional formula'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Print what would change without writing')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **opts):
        from api.services.encryption import encryption_service
        dry = opts['dry_run']
        bs = opts['batch_size']

        total = MoodNote.objects.count()
        updated = 0
        skipped = 0
        errors = 0
        scanned = 0

        self.stdout.write(f'Scanning {total} MoodNote rows...')

        # Iterate in batches to keep memory bounded
        last_id = 0
        while True:
            qs = (
                MoodNote.objects
                .filter(id__gt=last_id)
                .order_by('id')
                .values('id', 'encrypted_content', 'search_text')[:bs]
            )
            batch = list(qs)
            if not batch:
                break

            for row in batch:
                scanned += 1
                last_id = row['id']
                ct = row['encrypted_content']
                if not ct:
                    skipped += 1
                    continue
                try:
                    plain = encryption_service.decrypt(ct)
                except Exception:                                          # noqa: BLE001
                    errors += 1
                    continue
                new_st = MoodNote._make_search_text(plain)
                if new_st == row['search_text']:
                    skipped += 1
                    continue
                if not dry:
                    MoodNote.objects.filter(id=row['id']).update(search_text=new_st)
                updated += 1

            if scanned % 1000 == 0:
                self.stdout.write(
                    f'  ...scanned {scanned}/{total}, updated {updated}, '
                    f'skipped {skipped}, errors {errors}'
                )

        verb = 'Would update' if dry else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {verb} {updated} rows. Skipped {skipped} (already up to date or empty). '
            f'Errors {errors} (decrypt failure — likely legacy / pre-encryption rows).'
        ))
