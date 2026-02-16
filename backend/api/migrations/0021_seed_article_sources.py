# Data migration: add source citations to psycho education articles

from django.db import migrations

SOURCES = {
    'Introduction to Cognitive Distortions': 'Burns, D. D. (1980). Feeling Good: The New Mood Therapy. William Morrow.',
    'How to Reframe Negative Thoughts': 'Beck, J. S. (2011). Cognitive Behavior Therapy: Basics and Beyond (2nd ed.). Guilford Press.',
    '4-7-8 Breathing Technique': 'Weil, A. (2015). Breathing: The Master Key to Self Healing. Sounds True.',
    '5-4-3-2-1 Grounding Exercise': 'Najavits, L. M. (2002). Seeking Safety: A Treatment Manual for PTSD and Substance Abuse. Guilford Press.',
    'Emotion Identification and Acceptance': 'Gross, J. J. (2014). Handbook of Emotion Regulation (2nd ed.). Guilford Press.',
    'Introduction to Mindfulness Meditation': 'Kabat-Zinn, J. (1990). Full Catastrophe Living. Delacorte Press.',
    'Sleep Hygiene Guide': 'Walker, M. (2017). Why We Sleep: Unlocking the Power of Sleep and Dreams. Scribner.',
    'Stress Management Strategies': 'Lazarus, R. S., & Folkman, S. (1984). Stress, Appraisal, and Coping. Springer.',
}


def seed_sources(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    for title_en, source in SOURCES.items():
        PsychoArticle.objects.filter(title_en=title_en).update(source=source)


def unseed_sources(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    PsychoArticle.objects.filter(title_en__in=list(SOURCES.keys())).update(source='')


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_add_source_to_psychoarticle'),
    ]

    operations = [
        migrations.RunPython(seed_sources, unseed_sources),
    ]
