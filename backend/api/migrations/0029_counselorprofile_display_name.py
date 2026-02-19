from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_seed_breathing_course'),
    ]

    operations = [
        migrations.AddField(
            model_name='counselorprofile',
            name='display_name',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
