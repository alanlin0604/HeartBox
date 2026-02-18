# Data migration: fix dead article source URLs (SAMHSA 403, CDC sleep 404)

from django.db import migrations

NEW_SOURCES = {
    '5-4-3-2-1 Grounding Exercise': (
        'University of Rochester Medical Center (URMC). '
        'https://www.urmc.rochester.edu/behavioral-health-partners/bhp-blog/'
        'april-2018/5-4-3-2-1-coping-technique-for-anxiety'
    ),
    'Sleep Hygiene Guide': (
        'National Heart, Lung, and Blood Institute (NHLBI/NIH). '
        'https://www.nhlbi.nih.gov/health/sleep/healthy-sleep-habits'
    ),
}

OLD_SOURCES = {
    '5-4-3-2-1 Grounding Exercise': (
        'Substance Abuse and Mental Health Services Administration (SAMHSA). '
        'https://www.samhsa.gov/mental-health'
    ),
    'Sleep Hygiene Guide': (
        'Centers for Disease Control and Prevention (CDC). '
        'https://www.cdc.gov/sleep/about/sleep-hygiene.html'
    ),
}


def update_sources(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    for title_en, source in NEW_SOURCES.items():
        PsychoArticle.objects.filter(title_en=title_en).update(source=source)


def revert_sources(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    for title_en, source in OLD_SOURCES.items():
        PsychoArticle.objects.filter(title_en=title_en).update(source=source)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0022_update_article_sources'),
    ]

    operations = [
        migrations.RunPython(update_sources, revert_sources),
    ]
