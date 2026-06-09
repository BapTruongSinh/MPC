from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import Greenhouse, GreenhouseControlProfile


DEFAULT_GREENHOUSE_NAME = 'Main greenhouse'


def default_owner():
    owner = get_user_model().objects.order_by('id').first()
    if owner is not None:
        return owner

    owner = get_user_model().objects.create_user(username='system-greenhouse')
    owner.set_unusable_password()
    owner.save(update_fields=['password'])
    return owner


def ensure_user_greenhouse_config(user) -> tuple[Greenhouse, GreenhouseControlProfile]:
    greenhouse, _ = Greenhouse.objects.get_or_create(
        owner=user,
        name=DEFAULT_GREENHOUSE_NAME,
        defaults={'is_active': True},
    )
    profile, _ = GreenhouseControlProfile.objects.get_or_create(
        greenhouse=greenhouse,
        defaults={'singleton_key': f'gh-{greenhouse.pk}'},
    )
    return greenhouse, profile
