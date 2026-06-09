from django.conf import settings
from django.db import migrations, models


def remove_ownerless_profiles(apps, schema_editor):
    profile = apps.get_model('api', 'GreenhouseControlProfile')
    profile.objects.filter(owner_id__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0023_owner_scope_remove_greenhouse_fk'),
    ]

    operations = [
        migrations.RunPython(remove_ownerless_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='greenhousecontrolprofile',
            name='owner',
            field=models.OneToOneField(
                db_constraint=False,
                on_delete=models.CASCADE,
                related_name='control_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
