from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import GreenhouseControlProfile


def default_owner():
    user_model = get_user_model()
    owner = user_model.objects.filter(username='admin').order_by('-is_superuser', 'id').first()
    if owner is not None:
        return owner

    owner = user_model.objects.filter(is_superuser=True).order_by('id').first()
    if owner is not None:
        return owner

    owner = user_model.objects.order_by('id').first()
    if owner is not None:
        return owner

    owner = user_model.objects.create_user(username='admin')
    owner.set_unusable_password()
    owner.save(update_fields=['password'])
    return owner


def control_owner(user=None):
    return user if getattr(user, 'is_authenticated', False) else default_owner()


def ensure_user_control_profile(user) -> GreenhouseControlProfile:
    return GreenhouseControlProfile.objects.get_or_create(
        owner=user,
        defaults={'singleton_key': f'user-{user.pk}'},
    )[0]
