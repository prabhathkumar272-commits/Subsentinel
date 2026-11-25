from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import UserSettings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_settings(sender, instance, created, **kwargs):
    """Auto-create a UserSettings instance whenever a new user is created."""
    if created:
        UserSettings.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_settings(sender, instance, **kwargs):
    """Ensure the related UserSettings is saved when the user is saved."""
    try:
        instance.settings.save()
    except UserSettings.DoesNotExist:
        UserSettings.objects.create(user=instance)
