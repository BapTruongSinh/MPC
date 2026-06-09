from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0021_merge_esp32_thresholds_legacy_cleanup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devicecommand',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('ack', 'Acknowledged'),
                    ('failed', 'Failed'),
                    ('skipped', 'Skipped'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
