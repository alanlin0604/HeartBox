"""Scrub template leakage from historical LLM-generated rows.

Reason: workflow audit wf_ba1ab074-010 found that ``llm_server/engine.py``
used a fragile string-prefix prompt strip that failed silently and let the
entire chat template (``[INST]``, ``<<SYS>>``, ``assistant:`` …) leak into
consumer columns. The forward-going fix is a token-id slice + a
``scrub_llm_output`` defense at the provider chokepoint. This migration
applies the same scrub to existing rows so the historical pollution doesn't
keep re-surfacing in journal cards, AI chat history, and weekly summary
PDFs.

Idempotent: scrub is a no-op on already-clean strings, so re-running is safe.
Reverse is a no-op — there's no way to restore the original template-bearing
text and there's no reason anyone would want to.
"""
from django.db import migrations


def _scrub_rows(apps, schema_editor):
    from api.services.llm.sanitize import scrub_llm_output

    # MoodNote.ai_feedback ---------------------------------------------------
    MoodNote = apps.get_model('api', 'MoodNote')
    qs = MoodNote.objects.exclude(ai_feedback='').exclude(ai_feedback__isnull=True)
    updated = 0
    for note in qs.iterator(chunk_size=500):
        cleaned = scrub_llm_output(note.ai_feedback)
        if cleaned != note.ai_feedback:
            note.ai_feedback = cleaned
            note.save(update_fields=['ai_feedback'])
            updated += 1
    print(f'  MoodNote.ai_feedback scrubbed: {updated} rows')

    # AIChatMessage.content (only assistant role — user content is sacred) --
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
        print(f'  AIChatMessage(assistant).content scrubbed: {updated} rows')

    # WeeklySummary.ai_summary ----------------------------------------------
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
        print(f'  WeeklySummary.ai_summary scrubbed: {updated} rows')


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0055_customuser_age_band_customuser_consent_ai_training_and_more'),
    ]
    operations = [
        migrations.RunPython(_scrub_rows, reverse_code=migrations.RunPython.noop),
    ]
