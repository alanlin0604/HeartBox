"""Encrypt MoodNote.ai_feedback, AIChatMessage.content, WeeklySummary.ai_summary
at rest via Fernet (EncryptedTextField).

The AlterField operations change the Python field class but NOT the DB column
type — both ``TextField`` and ``EncryptedTextField`` map to ``text``. So this
migration is safe wrt schema lock contention even on large tables. The bulk
of the work is the RunPython that backfills existing plaintext rows into
ciphertext.

The backfill uses RAW SQL to read the plaintext (because at the point the
RunPython runs, Django sees the column as ``EncryptedTextField`` and
``from_db_value`` would try to decrypt a plaintext value and return it as
``'[Decryption failed]'`` after an InvalidToken log line). UPDATE goes
through the ORM so ``get_prep_value`` encrypts on the way back.

Idempotent: ``encryption_service.encrypt`` is guarded by an
``InvalidToken`` round-trip — if a value is already Fernet ciphertext, the
encrypt path is skipped (see ``EncryptedTextField.get_prep_value``).
"""
import api.services.encryption
from django.db import migrations


def _looks_like_fernet(value: str) -> bool:
    """Quick filter so we don't burn a try/except per row when the column
    is already ciphertext. Fernet tokens are URL-safe-base64 of a 73+ byte
    payload (1 version + 8 timestamp + 16 IV + ...) so they're always >= 90
    chars and start with ``gAAAAA``. Plaintext sentences rarely match both."""
    return isinstance(value, str) and len(value) >= 90 and value.startswith('gAAAAA')


def _try_decrypt(value):
    from api.services.encryption import encryption_service
    from cryptography.fernet import InvalidToken
    try:
        encryption_service.decrypt(value)
        return True
    except InvalidToken:
        return False


def _encrypt_table(apps, schema_editor, *, model_label, field_name):
    """Idempotently encrypt every row of ``model_label.field_name``."""
    from django.db import connection
    from api.services.encryption import encryption_service

    Model = apps.get_model('api', model_label)
    table = Model._meta.db_table

    # Raw SELECT to bypass EncryptedTextField.from_db_value (which would
    # log InvalidToken warnings on every plaintext row).
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT id, {field_name} FROM {table} '
            f"WHERE {field_name} IS NOT NULL AND {field_name} != ''"
        )
        rows = cursor.fetchall()

    encrypted = 0
    already = 0
    for pk, raw in rows:
        if raw is None or raw == '':
            continue
        # Already ciphertext? Skip.
        if _looks_like_fernet(raw) and _try_decrypt(raw):
            already += 1
            continue
        # Plaintext — encrypt and write back via raw UPDATE so we control
        # the bytes that hit the column (no double-encrypt via ORM path).
        ciphertext = encryption_service.encrypt(raw)
        with connection.cursor() as cursor:
            cursor.execute(
                f'UPDATE {table} SET {field_name} = %s WHERE id = %s',
                [ciphertext, pk],
            )
        encrypted += 1
    print(f'  {model_label}.{field_name}: encrypted {encrypted}, already-ciphertext {already}, total {len(rows)}')


def _encrypt_all(apps, schema_editor):
    _encrypt_table(apps, schema_editor, model_label='MoodNote', field_name='ai_feedback')
    _encrypt_table(apps, schema_editor, model_label='AIChatMessage', field_name='content')
    _encrypt_table(apps, schema_editor, model_label='WeeklySummary', field_name='ai_summary')


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0058_re_scrub_with_boundary_cut'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aichatmessage',
            name='content',
            field=api.services.encryption.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='moodnote',
            name='ai_feedback',
            field=api.services.encryption.EncryptedTextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='weeklysummary',
            name='ai_summary',
            field=api.services.encryption.EncryptedTextField(blank=True, default=''),
        ),
        # Backfill existing plaintext → Fernet ciphertext. Idempotent so
        # re-running on a partially-encrypted table is safe.
        migrations.RunPython(_encrypt_all, reverse_code=migrations.RunPython.noop),
    ]
