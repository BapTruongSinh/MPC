from __future__ import annotations

from django.conf import settings
from django.db import migrations, models


def _user_model(apps):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    return apps.get_model(app_label, model_name)


def _default_owner_id(apps) -> int:
    user_model = _user_model(apps)
    owner = user_model.objects.filter(is_superuser=True).order_by('id').first()
    if owner is None:
        owner = user_model.objects.order_by('id').first()
    if owner is None:
        owner = user_model.objects.create(
            username='admin',
            password='!',
            email='',
            is_staff=True,
            is_superuser=True,
        )
    return owner.pk


def _greenhouse_owner_map(apps) -> dict[int, int]:
    greenhouse = apps.get_model('api', 'Greenhouse')
    return dict(
        greenhouse.objects
        .exclude(owner_id__isnull=True)
        .values_list('id', 'owner_id')
    )


def _bulk_assign_owner(model, greenhouse_owner: dict[int, int], default_owner_id: int) -> None:
    updates = []
    for item in model.objects.only('id', 'greenhouse_id', 'owner_id').iterator(chunk_size=1000):
        owner_id = greenhouse_owner.get(item.greenhouse_id) or default_owner_id
        if item.owner_id == owner_id:
            continue
        item.owner_id = owner_id
        updates.append(item)
        if len(updates) >= 1000:
            model.objects.bulk_update(updates, ['owner'])
            updates.clear()
    if updates:
        model.objects.bulk_update(updates, ['owner'])


def _copy_runtime_scope(apps, schema_editor):
    default_owner_id = _default_owner_id(apps)
    greenhouse_owner = _greenhouse_owner_map(apps)

    for model_name in ('SensorData', 'EstimationCycle', 'AMPCRecommendation'):
        _bulk_assign_owner(apps.get_model('api', model_name), greenhouse_owner, default_owner_id)

    profile = apps.get_model('api', 'GreenhouseControlProfile')
    used_owner_ids = set()
    profile_updates = []
    for item in profile.objects.only('id', 'greenhouse_id', 'owner_id', 'updated_at').order_by('-updated_at', '-id'):
        owner_id = greenhouse_owner.get(item.greenhouse_id) or default_owner_id
        if owner_id in used_owner_ids:
            continue
        item.owner_id = owner_id
        used_owner_ids.add(owner_id)
        profile_updates.append(item)
    if profile_updates:
        profile.objects.bulk_update(profile_updates, ['owner'])

    user_model = _user_model(apps)
    for owner_id in user_model.objects.exclude(id__in=used_owner_ids).values_list('id', flat=True):
        key = f'user-{owner_id}'[:20]
        if profile.objects.filter(singleton_key=key).exists():
            key = f'owner-{owner_id}'[:20]
        profile.objects.create(owner_id=owner_id, singleton_key=key)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0022_devicecommand_skipped_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensordata',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=models.SET_NULL,
                related_name='sensor_readings',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='estimationcycle',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=models.SET_NULL,
                related_name='estimation_cycles',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='greenhousecontrolprofile',
            name='owner',
            field=models.OneToOneField(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=models.CASCADE,
                related_name='control_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='ampcrecommendation',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=models.SET_NULL,
                related_name='ampc_recommendations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(_copy_runtime_scope, migrations.RunPython.noop),
        migrations.RemoveField(model_name='sensordata', name='greenhouse'),
        migrations.RemoveField(model_name='estimationcycle', name='greenhouse'),
        migrations.RemoveField(model_name='greenhousecontrolprofile', name='greenhouse'),
        migrations.RemoveField(model_name='ampcrecommendation', name='greenhouse'),
        migrations.AlterModelOptions(
            name='greenhousecontrolprofile',
            options={'db_table': 'greenhouse_control_profiles'},
        ),
    ]
