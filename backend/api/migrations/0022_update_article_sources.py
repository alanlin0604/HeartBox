# Data migration: update article sources to internationally recognized organizations

from django.db import migrations

SOURCES = {
    'Introduction to Cognitive Distortions': 'American Psychological Association (APA). https://www.apa.org/ptsd-guideline/patients-and-families/cognitive-behavioral',
    'How to Reframe Negative Thoughts': 'National Institute of Mental Health (NIMH). https://www.nimh.nih.gov/health/topics/psychotherapies',
    '4-7-8 Breathing Technique': 'Harvard Medical School — Harvard Health Publishing. https://www.health.harvard.edu/lung-health-and-disease/learning-diaphragmatic-breathing',
    '5-4-3-2-1 Grounding Exercise': 'Substance Abuse and Mental Health Services Administration (SAMHSA). https://www.samhsa.gov/mental-health',
    'Emotion Identification and Acceptance': 'World Health Organization (WHO). https://www.who.int/news-room/fact-sheets/detail/mental-health-strengthening-our-response',
    'Introduction to Mindfulness Meditation': 'National Center for Complementary and Integrative Health (NCCIH/NIH). https://www.nccih.nih.gov/health/meditation-and-mindfulness-what-you-need-to-know',
    'Sleep Hygiene Guide': 'Centers for Disease Control and Prevention (CDC). https://www.cdc.gov/sleep/about/sleep-hygiene.html',
    'Stress Management Strategies': 'American Psychological Association (APA). https://www.apa.org/topics/stress',
}


def update_sources(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    for title_en, source in SOURCES.items():
        PsychoArticle.objects.filter(title_en=title_en).update(source=source)


def revert_sources(apps, schema_editor):
    # Revert to previous book-based sources
    OLD_SOURCES = {
        'Introduction to Cognitive Distortions': 'Burns, D. D. (1980). Feeling Good: The New Mood Therapy. William Morrow.',
        'How to Reframe Negative Thoughts': 'Beck, J. S. (2011). Cognitive Behavior Therapy: Basics and Beyond (2nd ed.). Guilford Press.',
        '4-7-8 Breathing Technique': 'Weil, A. (2015). Breathing: The Master Key to Self Healing. Sounds True.',
        '5-4-3-2-1 Grounding Exercise': 'Najavits, L. M. (2002). Seeking Safety: A Treatment Manual for PTSD and Substance Abuse. Guilford Press.',
        'Emotion Identification and Acceptance': 'Gross, J. J. (2014). Handbook of Emotion Regulation (2nd ed.). Guilford Press.',
        'Introduction to Mindfulness Meditation': 'Kabat-Zinn, J. (1990). Full Catastrophe Living. Delacorte Press.',
        'Sleep Hygiene Guide': 'Walker, M. (2017). Why We Sleep: Unlocking the Power of Sleep and Dreams. Scribner.',
        'Stress Management Strategies': 'Lazarus, R. S., & Folkman, S. (1984). Stress, Appraisal, and Coping. Springer.',
    }
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    for title_en, source in OLD_SOURCES.items():
        PsychoArticle.objects.filter(title_en=title_en).update(source=source)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0021_seed_article_sources'),
    ]

    operations = [
        migrations.RunPython(update_sources, revert_sources),
    ]
