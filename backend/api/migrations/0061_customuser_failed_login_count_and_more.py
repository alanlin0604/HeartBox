"""Batch F security migration:
  * Encrypt TOTPDevice.secret (2FA key material — biggest standalone leak)
  * Add CustomUser.failed_login_count + locked_until for account lockout
  * Create TOTPBackupCode for 2FA recovery flow (closes the UX trap where
    a user who lost their authenticator could not disable 2FA)

The AlterField on totpdevice.secret only changes Python field class — DB
column type stays text — so the schema lock is trivial. The RunPython
backfill is the same idempotent pattern as 0059 / 0060: raw SELECT bypasses
the new from_db_value, encrypt plaintext, write back via ORM so
get_prep_value adds the Fernet wrapping. Idempotent (Fernet shape + try-
decrypt guard).
"""
import api.services.encryption
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _looks_like_fernet(value):
    return isinstance(value, str) and len(value) >= 90 and value.startswith('gAAAAA')


def _encrypt_totp_secrets(apps, schema_editor):
    from django.db import connection
    from api.services.encryption import encryption_service

    Model = apps.get_model('api', 'TOTPDevice')
    table = Model._meta.db_table

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id, secret FROM {table} "
            f"WHERE secret IS NOT NULL AND secret != ''"
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
                f'UPDATE {table} SET secret = %s WHERE id = %s',
                [ciphertext, pk],
            )
        encrypted += 1
    print(f'  TOTPDevice.secret: encrypted {encrypted}, already {already}, total {len(rows)}')


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0060_alter_friendcomment_content_alter_message_content_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='failed_login_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customuser',
            name='locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='totpdevice',
            name='secret',
            field=api.services.encryption.EncryptedTextField(),
        ),
        migrations.CreateModel(
            name='TOTPBackupCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=128)),
                ('used', models.BooleanField(default=False)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='totp_backup_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['user', 'used'], name='totpbackup_user_used')],
            },
        ),
        # Backfill existing plaintext TOTP secrets into Fernet ciphertext.
        migrations.RunPython(_encrypt_totp_secrets, reverse_code=migrations.RunPython.noop),
    ]
