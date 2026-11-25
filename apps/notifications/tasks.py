"""Celery tasks for sending reminders and advancing billing dates."""

from __future__ import annotations

from datetime import date

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q

from apps.notifications.models import Notification, NotificationType, ReminderLog, ReminderType
from apps.subscriptions.models import PaymentRecord, Subscription, SubscriptionStatus
from apps.subscriptions.services import advance_billing_date


@shared_task
def check_upcoming_renewals():
    """Create notifications for subscriptions renewing within the user's reminder window.

    * Finds active subscriptions where ``next_billing_date`` is within
      ``reminder_days_before`` days of today.
    * Checks :model:`ReminderLog` to prevent sending duplicate reminders.
    * Creates an in-app :model:`Notification` and sends an email if the
      user has ``email_reminders_enabled``.
    """
    today = date.today()
    active_subs = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
    ).select_related('user', 'user__settings')

    for sub in active_subs:
        days_until = (sub.next_billing_date - today).days
        reminder_days = sub.reminder_days_before

        if 0 <= days_until <= reminder_days:
            # Check for existing reminder
            already_sent = ReminderLog.objects.filter(
                subscription=sub,
                reminder_date=sub.next_billing_date,
                reminder_type=ReminderType.RENEWAL,
            ).exists()

            if already_sent:
                continue

            # Create notification
            Notification.objects.create(
                user=sub.user,
                title=f'Upcoming renewal: {sub.name}',
                message=(
                    f'Your {sub.get_billing_cycle_display().lower()} subscription '
                    f'to {sub.name} ({sub.currency} {sub.amount}) renews on '
                    f'{sub.next_billing_date.strftime("%b %d, %Y")}.'
                ),
                notification_type=NotificationType.RENEWAL,
                related_subscription=sub,
            )

            # Send email if enabled
            try:
                user_settings = sub.user.settings
            except Exception:
                user_settings = None

            if user_settings and user_settings.email_reminders_enabled:
                send_mail(
                    subject=f'[SubSentinel] Upcoming renewal: {sub.name}',
                    message=(
                        f'Hi {sub.user.first_name or sub.user.email},\n\n'
                        f'Your subscription to {sub.name} '
                        f'({sub.currency} {sub.amount}) renews on '
                        f'{sub.next_billing_date.strftime("%b %d, %Y")}.\n\n'
                        f'– SubSentinel'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[sub.user.email],
                    fail_silently=True,
                )

            # Log the reminder
            ReminderLog.objects.create(
                subscription=sub,
                reminder_date=sub.next_billing_date,
                reminder_type=ReminderType.RENEWAL,
            )


@shared_task
def advance_billing_dates():
    """Advance billing dates for subscriptions that have passed their renewal.

    For each active subscription whose ``next_billing_date`` is in the
    past, creates a :model:`PaymentRecord` and advances the date by one
    billing cycle.
    """
    today = date.today()
    overdue = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        next_billing_date__lt=today,
    )

    for sub in overdue:
        # Record the payment
        PaymentRecord.objects.create(
            subscription=sub,
            amount=sub.amount,
            date=sub.next_billing_date,
            notes='Auto-recorded by SubSentinel',
        )

        # Advance to next cycle
        advance_billing_date(sub)


@shared_task
def check_expiring_trials():
    """Create notifications for free trials ending within the user's reminder window."""
    today = date.today()
    trial_subs = Subscription.objects.filter(
        Q(is_trial=True) | Q(status='trial'),
        status__in=[SubscriptionStatus.ACTIVE, 'trial'],
        trial_end_date__isnull=False,
    ).select_related('user', 'user__settings')

    for sub in trial_subs:
        days_until = (sub.trial_end_date - today).days
        reminder_days = sub.reminder_days_before

        if 0 <= days_until <= reminder_days:
            already_sent = ReminderLog.objects.filter(
                subscription=sub,
                reminder_date=sub.trial_end_date,
                reminder_type=ReminderType.TRIAL,
            ).exists()

            if already_sent:
                continue

            Notification.objects.create(
                user=sub.user,
                title=f'Trial ending soon: {sub.name}',
                message=(
                    f'Your free trial for {sub.name} ends on '
                    f'{sub.trial_end_date.strftime("%b %d, %Y")}. '
                    f'You will be charged {sub.currency} {sub.amount} unless cancelled.'
                ),
                notification_type=NotificationType.TRIAL_ENDING,
                related_subscription=sub,
            )

            try:
                user_settings = sub.user.settings
            except Exception:
                user_settings = None

            if user_settings and user_settings.email_reminders_enabled:
                send_mail(
                    subject=f'[SubSentinel] Trial ending soon: {sub.name}',
                    message=(
                        f'Hi {sub.user.first_name or sub.user.email},\n\n'
                        f'Your free trial for {sub.name} ends on '
                        f'{sub.trial_end_date.strftime("%b %d, %Y")}.\n\n'
                        f'– SubSentinel'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[sub.user.email],
                    fail_silently=True,
                )

            ReminderLog.objects.create(
                subscription=sub,
                reminder_date=sub.trial_end_date,
                reminder_type=ReminderType.TRIAL,
            )
