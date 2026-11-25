from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.managers import CustomUserManager


class CustomUser(AbstractUser):
    """Custom user model that uses email as the unique identifier."""

    username = None
    email = models.EmailField('email address', unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self) -> str:
        return self.email


class UserSettings(models.Model):
    """Per-user preferences for currency, reminders, and UI theme."""

    class Currency(models.TextChoices):
        USD = 'USD', 'US Dollar'
        EUR = 'EUR', 'Euro'
        GBP = 'GBP', 'British Pound'
        INR = 'INR', 'Indian Rupee'
        CAD = 'CAD', 'Canadian Dollar'
        AUD = 'AUD', 'Australian Dollar'
        JPY = 'JPY', 'Japanese Yen'

    class Theme(models.TextChoices):
        LIGHT = 'light', 'Light'
        DARK = 'dark', 'Dark'
        SYSTEM = 'system', 'System'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings',
    )
    default_currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
    )
    default_reminder_days = models.PositiveIntegerField(default=3)
    email_reminders_enabled = models.BooleanField(default=True)
    theme = models.CharField(
        max_length=6,
        choices=Theme.choices,
        default=Theme.SYSTEM,
    )

    class Meta:
        verbose_name = 'user settings'
        verbose_name_plural = 'user settings'

    def __str__(self) -> str:
        return f'Settings for {self.user.email}'
