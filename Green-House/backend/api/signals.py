from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .user_resources import ensure_user_control_profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_control_profile(sender, instance, created, **kwargs):
    if created:
        ensure_user_control_profile(instance)
