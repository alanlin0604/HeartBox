"""Re-scrub historical LLM-generated rows now that ``scrub_llm_output`` has
the prompt-boundary cut (commit 0749431).

Migration 0056 ran before the boundary cut existed; it stripped ``[INST]``
markers from historical rows but left the system-prompt body + user-message
``日記內容：「...」`` wrapper. The user's 11:42 screenshot showed this
post-marker-scrub residue in NoteDetailPage. This migration re-applies the
NEW scrub, which now also performs the boundary cut and yields the bare
assistant reply.

Idempotent: clean rows are no-ops. Safe to re-run.
"""
from django.db import migrations


def _rescrub(apps, schema_editor):
    from api.services.llm.sanitize import scrub_llm_output

    MoodNote = apps.get_model('api', 'MoodNote')
    qs = MoodNote.objects.exclude(ai_feedback='').exclude(ai_feedback__isnull=True)
    updated = 0
    for note in qs.iterator(chunk_size=500):
        cleaned = scrub_llm_output(note.ai_feedback)
        if cleaned != note.ai_feedback:
            note.ai_feedback = cleaned
            note.save(update_fields=['ai_feedback'])
            updated += 1
    print(f'  MoodNote.ai_feedback re-scrubbed: {updated} rows')

    try:
        AIChatMessage = apps.get_model('api', 'AIChatMessage')
    except LookupError:
        AIChatMessage = None
    if AIChatMessage is not None:
        qs = AIChatMessage.objects.filter(role='assistant').exclude(content='')
        updated = 0
        for msg in qs.iterator(chunk_size=500):
            cleaned = scrub_llm_output(msg.content)
            if cleaned != msg.content:
                msg.content = cleaned
                msg.save(update_fields=['content'])
                updated += 1
        print(f'  AIChatMessage(assistant).content re-scrubbed: {updated} rows')

    try:
        WeeklySummary = apps.get_model('api', 'WeeklySummary')
    except LookupError:
        WeeklySummary = None
    if WeeklySummary is not None:
        qs = WeeklySummary.objects.exclude(ai_summary='').exclude(ai_summary__isnull=True)
        updated = 0
        for summary in qs.iterator(chunk_size=500):
            cleaned = scrub_llm_output(summary.ai_summary)
            if cleaned != summary.ai_summary:
                summary.ai_summary = cleaned
                summary.save(update_fields=['ai_summary'])
                updated += 1
        print(f'  WeeklySummary.ai_summary re-scrubbed: {updated} rows')


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0057_alter_auditlog_target_id'),
    ]
    operations = [
        migrations.RunPython(_rescrub, reverse_code=migrations.RunPython.noop),
    ]
