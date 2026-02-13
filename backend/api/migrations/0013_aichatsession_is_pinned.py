from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_userachievement_and_pricing'),
    ]

    operations = [
        migrations.AddField(
            model_name='aichatsession',
            name='is_pinned',
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveIndex(
            model_name='aichatsession',
            name='aichat_user_updated',
        ),
        migrations.AddIndex(
            model_name='aichatsession',
            index=models.Index(fields=['user', '-is_pinned', '-updated_at'], name='aichat_user_pin_upd'),
        ),
        migrations.AlterModelOptions(
            name='aichatsession',
            options={'ordering': ['-is_pinned', '-updated_at']},
        ),
    ]
