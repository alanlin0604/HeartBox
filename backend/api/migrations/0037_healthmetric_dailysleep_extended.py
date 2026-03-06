from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0036_counselorreview_rating_validators'),
    ]

    operations = [
        # Add new fields to DailySleep
        migrations.AddField(
            model_name='dailysleep',
            name='bedtime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dailysleep',
            name='wake_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dailysleep',
            name='deep_sleep_minutes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dailysleep',
            name='light_sleep_minutes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dailysleep',
            name='rem_sleep_minutes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dailysleep',
            name='source',
            field=models.CharField(default='manual', max_length=50),
        ),
        # Create HealthMetric model
        migrations.CreateModel(
            name='HealthMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('metric_type', models.CharField(
                    choices=[
                        ('steps', 'Steps'),
                        ('heart_rate', 'Heart Rate'),
                        ('hrv', 'Heart Rate Variability'),
                        ('active_calories', 'Active Calories'),
                        ('exercise_minutes', 'Exercise Minutes'),
                    ],
                    max_length=30,
                )),
                ('value', models.FloatField()),
                ('source', models.CharField(default='manual', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='health_metrics',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-date'],
                'unique_together': {('user', 'date', 'metric_type')},
                'indexes': [
                    models.Index(fields=['user', 'date'], name='healthmetric_user_date'),
                    models.Index(fields=['user', 'metric_type', '-date'], name='healthmetric_user_type_date'),
                ],
            },
        ),
    ]
