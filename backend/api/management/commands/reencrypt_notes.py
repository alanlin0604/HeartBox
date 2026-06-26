"""Key-rotation playbook.

After rotating ENCRYPTION_KEY (a MultiFernet key list where the new key is
PRIMARY and the old key is kept SECONDARY for decryption), run this command
to re-encrypt every Fernet ciphertext in the schema using the new primary
key. Once it finishes, the old key can safely be removed from
ENCRYPTION_KEY.

WHAT GETS REWRITTEN
  * MoodNote.encrypted_content      (journal body)
  * MoodNote.ai_feedback            (AI reply)
  * AIChatMessage.content           (chat — both roles)
  * WeeklySummary.ai_summary        (week-level synthesis)
  * Message.content                 (DMs)
  * FriendComment.content
  * Notification.message
  * PostReport.note
  * TOTPDevice.secret               (2FA seed)

DESIGN
  * Decrypt via MultiFernet (tries every key in order) → encrypt with
    the new primary. If MultiFernet can't decrypt, the row is logged and
    skipped (don't blow up the rotation on one corrupt row).
  * Chunked iterator (default 500) so a 100k-row table doesn't blow up
    Python memory.
  * Resumable: pass --from-id N to skip rows below that PK. Combined
    with a stable ORDER BY pk, an interrupted run can resume cleanly.
  * --dry-run reports counts without writing.
  * Per-model output so an operator can see progress in long runs.

USAGE
    python manage.py reencrypt_notes                       # all tables
    python manage.py reencrypt_notes --dry-run             # estimate only
    python manage.py reencrypt_notes --model MoodNote      # one table
    python manage.py reencrypt_notes --from-id 50000       # resume
    python manage.py reencrypt_notes --chunk-size 200      # smaller batches

EXIT
  0 if every row processed cleanly.
  1 if one or more rows failed to decrypt (logged with model/pk).
"""
from __future__ import annotations

import logging

from cryptography.fernet import InvalidToken
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

logger = logging.getLogger(__name__)

# (model_label, column_name) pairs. Each is iterated via raw SQL so we
# bypass EncryptedTextField.from_db_value (which would re-encrypt before we
# see the source bytes) and bypass get_prep_value on update (which would
# log InvalidToken on idempotent re-runs).
ENCRYPTED_COLUMNS = [
    ('MoodNote', 'encrypted_content'),
    ('MoodNote', 'ai_feedback'),
    ('AIChatMessage', 'content'),
    ('WeeklySummary', 'ai_summary'),
    ('Message', 'content'),
    ('FriendComment', 'content'),
    ('Notification', 'message'),
    ('PostReport', 'note'),
    ('TOTPDevice', 'secret'),
]


class Command(BaseCommand):
    help = 'Re-encrypt every Fernet ciphertext column with the primary ENCRYPTION_KEY.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Count rows but do not write back.',
        )
        parser.add_argument(
            '--model', type=str, default=None,
            help='Only process this model label (e.g. MoodNote). Default: all.',
        )
        parser.add_argument(
            '--from-id', type=int, default=0,
            help='Resume: skip rows with pk < FROM_ID.',
        )
        parser.add_argument(
            '--chunk-size', type=int, default=500,
            help='Rows per SELECT chunk. Default 500.',
        )

    def handle(self, *args, **opts):
        from django.apps import apps as django_apps
        from api.services.encryption import encryption_service

        dry = bool(opts['dry_run'])
        only = opts['model']
        from_id = int(opts['from_id'])
        chunk = max(1, int(opts['chunk_size']))

        total_rewritten = 0
        total_skipped = 0
        total_failed = 0

        for model_label, field in ENCRYPTED_COLUMNS:
            if only and only != model_label:
                continue
            try:
                Model = django_apps.get_model('api', model_label)
            except LookupError:
                self.stderr.write(f'  ⚠ Model api.{model_label} not found — skipping')
                continue
            table = Model._meta.db_table
            self.stdout.write(f'\n→ {model_label}.{field}  ({table})')

            rewritten = skipped = failed = 0
            last_id = max(0, from_id - 1)
            while True:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f'SELECT id, {field} FROM {table} '
                        f'WHERE id > %s AND {field} IS NOT NULL AND {field} != %s '
                        f'ORDER BY id LIMIT %s',
                        [last_id, '', chunk],
                    )
                    rows = cursor.fetchall()
                if not rows:
                    break

                for pk, raw in rows:
                    last_id = pk
                    plain = encryption_service.try_decrypt(raw)
                    if plain is None:
                        # MultiFernet couldn't decrypt with any active key.
                        # Likely garbage; do NOT touch.
                        logger.error(
                            'reencrypt_notes: %s.%s pk=%s decrypt FAILED — skipping',
                            model_label, field, pk,
                        )
                        failed += 1
                        continue
                    # Re-encrypt with the current PRIMARY key. If the row was
                    # already encrypted with the primary, the resulting
                    # ciphertext just has a fresh IV — still valid, but the
                    # rewrite is wasted IO. We accept the waste (Fernet doesn't
                    # expose which key encrypted a given token).
                    if dry:
                        rewritten += 1
                        continue
                    new_ciphertext = encryption_service.encrypt(plain)
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f'UPDATE {table} SET {field} = %s WHERE id = %s',
                            [new_ciphertext, pk],
                        )
                    rewritten += 1

            self.stdout.write(
                f'   rewritten={rewritten}  skipped={skipped}  failed={failed}'
                + ('  [DRY-RUN]' if dry else '')
            )
            total_rewritten += rewritten
            total_skipped += skipped
            total_failed += failed

        self.stdout.write(self.style.SUCCESS(
            f'\nTOTAL  rewritten={total_rewritten}  failed={total_failed}'
            + ('  [DRY-RUN — nothing actually written]' if dry else '')
        ))
        if total_failed:
            raise CommandError(
                f'{total_failed} row(s) failed to decrypt. Inspect logs and '
                'either repair the rows or keep the old key in ENCRYPTION_KEY.'
            )
