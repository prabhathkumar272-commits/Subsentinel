"""Celery tasks for reminders and expected billing events."""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.notifications.models import Notification, NotificationType, ReminderLog, ReminderType
from apps.subscriptions.models import PaymentRecord, PaymentStatus, Subscription, SubscriptionStatus
from apps.subscriptions.services import advance_billing_date

logger = logging.getLogger(__name__)


def _create_reminder(sub, reminder_date, reminder_type, title, message):
    """Create a reminder and its notification once, despite concurrent runs."""
    with transaction.atomic():
        reminder, created = ReminderLog.objects.get_or_create(
            subscription=sub,
            reminder_date=reminder_date,
            reminder_type=reminder_type,
        )
        if created:
            Notification.objects.create(
                user=sub.user,
                title=title,
                message=message,
                notification_type=(
                    NotificationType.RENEWAL
                    if reminder_type == ReminderType.RENEWAL
                    else NotificationType.TRIAL_ENDING
                ),
                related_subscription=sub,
            )
    return reminder


def _send_reminder_email(sub, reminder, subject, message):
    """Send reminder mail and record success so failed sends can retry later."""
    user_settings = getattr(sub.user, 'settings', None)
    if not user_settings or not user_settings.email_reminders_enabled or reminder.email_sent_at:
        return
    try:
        delivered = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[sub.user.email],
            fail_silently=False,
        )
        if delivered == 0:
            logger.warning('Reminder email was not accepted for subscription %s', sub.pk)
            return
    except Exception:
        logger.exception('Failed to send %s reminder email for subscription %s', reminder.reminder_type, sub.pk)
        return
    reminder.email_sent_at = timezone.now()
    reminder.save(update_fields=['email_sent_at'])


@shared_task
def check_upcoming_renewals():
    """Create in-app and email reminders inside each subscription's window."""
    today = timezone.localdate()
    active_subs = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
    ).select_related('user', 'user__settings')

    for sub in active_subs:
        if not 0 <= (sub.next_billing_date - today).days <= sub.reminder_days_before:
            continue
        due_date = sub.next_billing_date
        reminder = _create_reminder(
            sub,
            due_date,
            ReminderType.RENEWAL,
            f'Upcoming renewal: {sub.name}',
            (
                f'Your {sub.get_billing_cycle_display().lower()} subscription '
                f'to {sub.name} ({sub.currency} {sub.amount}) renews on '
                f'{due_date.strftime("%b %d, %Y")}.'
            ),
        )
        _send_reminder_email(
            sub,
            reminder,
            f'[SubSentinel] Upcoming renewal: {sub.name}',
            (
                f'Hi {sub.user.first_name or sub.user.email},\n\n'
                f'Your subscription to {sub.name} ({sub.currency} {sub.amount}) '
                f'renews on {due_date.strftime("%b %d, %Y")}.\n\n– SubSentinel'
            ),
        )


@shared_task
def advance_billing_dates():
    """Create expected renewal events idempotently and advance overdue dates.

    Expected rows are not represented as confirmed payments. Each subscription
    row is locked and the events plus schedule advancement share one transaction.
    """
    today = timezone.localdate()
    overdue_ids = list(
        Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            next_billing_date__lt=today,
        ).values_list('pk', flat=True)
    )

    for subscription_id in overdue_ids:
        with transaction.atomic():
            sub = (
                Subscription.objects.select_for_update()
                .filter(
                    pk=subscription_id,
                    status=SubscriptionStatus.ACTIVE,
                    next_billing_date__lt=today,
                )
                .first()
            )
            if sub is None:
                continue

            # Backfill all missed cycles. The DB constraint is a second line of
            # defense if a task is retried or run concurrently.
            while sub.next_billing_date < today:
                billing_date = sub.next_billing_date
                PaymentRecord.objects.get_or_create(
                    subscription=sub,
                    date=billing_date,
                    status=PaymentStatus.EXPECTED,
                    defaults={
                        'amount': sub.amount,
                        'currency': sub.currency,
                        'notes': 'Expected renewal; confirm only after the charge appears on your statement.',
                    },
                )
                advance_billing_date(sub)


@shared_task
def check_expiring_trials():
    """Create reminders for free trials ending inside each user's reminder window."""
    today = timezone.localdate()
    trial_subs = Subscription.objects.filter(
        Q(is_trial=True) | Q(status='trial'),
        status__in=[SubscriptionStatus.ACTIVE, 'trial'],
        trial_end_date__isnull=False,
    ).select_related('user', 'user__settings')

    for sub in trial_subs:
        if not 0 <= (sub.trial_end_date - today).days <= sub.reminder_days_before:
            continue
        reminder = _create_reminder(
            sub,
            sub.trial_end_date,
            ReminderType.TRIAL,
            f'Trial ending soon: {sub.name}',
            (
                f'Your free trial for {sub.name} ends on '
                f'{sub.trial_end_date.strftime("%b %d, %Y")}. '
                f'You may be charged {sub.currency} {sub.amount} unless cancelled.'
            ),
        )
        _send_reminder_email(
            sub,
            reminder,
            f'[SubSentinel] Trial ending soon: {sub.name}',
            (
                f'Hi {sub.user.first_name or sub.user.email},\n\n'
                f'Your free trial for {sub.name} ends on '
                f'{sub.trial_end_date.strftime("%b %d, %Y")}.\n\n– SubSentinel'
            ),
        )
