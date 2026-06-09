from django.conf import settings
from django.db import migrations


def seed_user_greenhouse_configs(apps, schema_editor):
    Greenhouse = apps.get_model('api', 'Greenhouse')
    GreenhouseControlProfile = apps.get_model('api', 'GreenhouseControlProfile')

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT `id` FROM `auth_user` ORDER BY `id`")
        user_ids = [row[0] for row in cursor.fetchall()]

    for user_id in user_ids:
        greenhouse, _ = Greenhouse.objects.get_or_create(
            owner_id=user_id,
            name='Main greenhouse',
            defaults={'is_active': True},
        )
        GreenhouseControlProfile.objects.get_or_create(
            greenhouse=greenhouse,
            defaults={'singleton_key': f'gh-{greenhouse.pk}'},
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0014_restore_greenhouse_profile_scope'),
    ]

    operations = [
        migrations.RunPython(seed_user_greenhouse_configs, migrations.RunPython.noop),
    ]
