from django.conf import settings
from django.db import migrations


def _user_model(apps):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    return apps.get_model(app_label, model_name)


def _admin_owner_id(apps) -> int | None:
    user_model = _user_model(apps)
    admin = user_model.objects.filter(username='admin').order_by('-is_superuser', 'id').first()
    return admin.pk if admin is not None else None


def pin_runtime_data_to_admin(apps, schema_editor):
    admin_id = _admin_owner_id(apps)
    if admin_id is None:
        return

    for model_name in ('SensorData', 'EstimationCycle', 'AMPCRecommendation'):
        apps.get_model('api', model_name).objects.update(owner_id=admin_id)

    profile = apps.get_model('api', 'GreenhouseControlProfile')
    if not profile.objects.filter(owner_id=admin_id).exists():
        profile.objects.create(owner_id=admin_id, singleton_key=f'user-{admin_id}'[:20])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0024_require_control_profile_owner'),
    ]

    operations = [
        migrations.RunPython(pin_runtime_data_to_admin, migrations.RunPython.noop),
    ]
