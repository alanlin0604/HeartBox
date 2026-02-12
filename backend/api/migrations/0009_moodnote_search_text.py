from django.db import migrations, models


def populate_search_text(apps, schema_editor):
    """Fill search_text for existing notes by decrypting content."""
    MoodNote = apps.get_model('api', 'MoodNote')
    from api.services.encryption import encryption_service

    for note in MoodNote.objects.all().iterator():
        try:
            plaintext = encryption_service.decrypt(note.encrypted_content)
            note.search_text = plaintext[:200]
            note.save(update_fields=['search_text'])
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_add_indexes_message_booking_timeslot'),
    ]

    operations = [
        migrations.AddField(
            model_name='moodnote',
            name='search_text',
            field=models.TextField(blank=True, default='', help_text='Plaintext index (first 200 chars) for DB-level search'),
        ),
        migrations.AddIndex(
            model_name='moodnote',
            index=models.Index(fields=['user', 'search_text'], name='moodnote_user_search'),
        ),
        migrations.RunPython(populate_search_text, migrations.RunPython.noop),
    ]
