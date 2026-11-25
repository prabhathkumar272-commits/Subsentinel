from django.conf import settings
from django.db import models

from apps.subscriptions.models import Subscription


class NotificationType(models.TextChoices):
    RENEWAL = 'renewal', 'Renewal'
    TRIAL_ENDING = 'trial_ending', 'Trial Ending'
    PRICE_CHANGE = 'price_change', 'Price Change'
    GENERAL = 'general', 'General'


class Notification(models.Model):
    """In-app notification for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=15,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True)
    related_subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.title} – {"read" if self.is_read else "unread"}'


class ReminderType(models.TextChoices):
    RENEWAL = 'renewal', 'Renewal'
    TRIAL = 'trial', 'Trial'


class ReminderLog(models.Model):
    """Log of sent reminders to prevent duplicate notifications."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='reminder_logs',
    )
    reminder_date = models.DateField()
    reminder_type = models.CharField(max_length=10, choices=ReminderType.choices)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['subscription', 'reminder_date', 'reminder_type']

    def __str__(self) -> str:
        return f'{self.subscription.name} – {self.get_reminder_type_display()} on {self.reminder_date}'
