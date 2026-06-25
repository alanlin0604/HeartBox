"""Fernet-encrypt FriendComment.content / Message.content (DM) /
Notification.message / PostReport.note at rest.

Same pattern as 0059 (which encrypted MoodNote.ai_feedback /
AIChatMessage.content / WeeklySummary.ai_summary): AlterField changes the
Python field class only — both ``TextField`` and ``EncryptedTextField`` map
to ``text`` at the DB layer — and a follow-up RunPython encrypts any
plaintext value that's still in the column.

Idempotent: ``EncryptedTextField.get_prep_value`` skips re-encryption when
the value is already a valid Fernet ciphertext. Backfill uses raw SQL on
the read path so plaintext rows don't trigger noisy InvalidToken warnings
in ``from_db_value``.
"""
import api.services.encryption
from django.db import migrations


def _looks_like_fernet(value):
    return isinstance(value, str) and len(value) >= 90 and value.startswith('gAAAAA')


def _encrypt_table(apps, schema_editor, *, model_label, field_name):
    from django.db import connection
    from api.services.encryption import encryption_service

    Model = apps.get_model('api', model_label)
    table = Model._meta.db_table

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id, {field_name} FROM {table} "
            f"WHERE {field_name} IS NOT NULL AND {field_name} != ''"
        )
        rows = cursor.fetchall()

    encrypted = already = 0
    for pk, raw in rows:
        if raw is None or raw == '':
            continue
        if _looks_like_fernet(raw) and encryption_service.try_decrypt(raw) is not None:
            already += 1
            continue
        ciphertext = encryption_service.encrypt(raw)
        with connection.cursor() as cursor:
            cursor.execute(
                f'UPDATE {table} SET {field_name} = %s WHERE id = %s',
                [ciphertext, pk],
            )
        encrypted += 1
    print(f'  {model_label}.{field_name}: encrypted {encrypted}, already {already}, total {len(rows)}')


def _encrypt_all(apps, schema_editor):
    _encrypt_table(apps, schema_editor, model_label='FriendComment', field_name='content')
    _encrypt_table(apps, schema_editor, model_label='Message', field_name='content')
    _encrypt_table(apps, schema_editor, model_label='Notification', field_name='message')
    _encrypt_table(apps, schema_editor, model_label='PostReport', field_name='note')


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0059_alter_aichatmessage_content_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='friendcomment',
            name='content',
            field=api.services.encryption.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='message',
            name='content',
            field=api.services.encryption.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='notification',
            name='message',
            field=api.services.encryption.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='postreport',
            name='note',
            field=api.services.encryption.EncryptedTextField(blank=True, default=''),
        ),
        migrations.RunPython(_encrypt_all, reverse_code=migrations.RunPython.noop),
    ]
