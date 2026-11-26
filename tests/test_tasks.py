from datetime import date, timedelta
from unittest.mock import patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Reminder / notification tasks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestReminderTasks:
    def test_check_upcoming_renewals_creates_notification(self, user, subscription):
        from apps.notifications.tasks import check_upcoming_renewals

        # Put the subscription inside the reminder window
        subscription.next_billing_date = date.today() + timedelta(days=2)
        subscription.reminder_days_before = 3
        subscription.save()

        check_upcoming_renewals()

        from apps.notifications.models import Notification
        notif = Notification.objects.filter(user=user).first()
        assert notif is not None

    def test_failed_reminder_email_retries_without_duplicate_notification(self, user, subscription):
        from apps.notifications.models import Notification, ReminderLog
        from apps.notifications.tasks import check_upcoming_renewals

        subscription.next_billing_date = date.today() + timedelta(days=2)
        subscription.save(update_fields=['next_billing_date'])
        with patch('apps.notifications.tasks.send_mail', side_effect=[OSError('SMTP unavailable'), 1]) as send_mail:
            check_upcoming_renewals()
            reminder = ReminderLog.objects.get(subscription=subscription)
            assert reminder.email_sent_at is None
            check_upcoming_renewals()

        reminder.refresh_from_db()
        assert send_mail.call_count == 2
        assert reminder.email_sent_at is not None
        assert Notification.objects.filter(user=user, notification_type='renewal').count() == 1

    def test_overdue_cycles_are_expected_and_idempotent(self, subscription):
        from apps.notifications.tasks import advance_billing_dates
        from apps.subscriptions.models import PaymentRecord, PaymentStatus

        initial_date = date.today() - timedelta(days=65)
        subscription.next_billing_date = initial_date
        subscription.save(update_fields=['next_billing_date'])

        advance_billing_dates()
        first_count = PaymentRecord.objects.filter(subscription=subscription).count()
        assert first_count == 3
        assert PaymentRecord.objects.filter(subscription=subscription, status=PaymentStatus.EXPECTED).count() == 3
        assert not PaymentRecord.objects.filter(subscription=subscription, status=PaymentStatus.CONFIRMED).exists()
        assert all(
            record.confirmed_at is None and record.currency == subscription.currency
            for record in PaymentRecord.objects.filter(subscription=subscription)
        )

        advance_billing_dates()
        assert PaymentRecord.objects.filter(subscription=subscription).count() == first_count

    def test_no_duplicate_reminders(self, user, subscription):
        from apps.notifications.models import Notification
        from apps.notifications.tasks import check_upcoming_renewals

        subscription.next_billing_date = date.today() + timedelta(days=2)
        subscription.reminder_days_before = 3
        subscription.save()

        # Run twice – should still produce only one notification
        check_upcoming_renewals()
        check_upcoming_renewals()

        count = Notification.objects.filter(
            user=user,
            notification_type='renewal',
        ).count()
        assert count == 1

    def test_no_notification_outside_window(self, user, subscription, category):
        from apps.notifications.models import Notification
        from apps.notifications.tasks import check_upcoming_renewals

        # 10 days away, reminder window is 3 days
        subscription.next_billing_date = date.today() + timedelta(days=10)
        subscription.reminder_days_before = 3
        subscription.save()

        check_upcoming_renewals()

        count = Notification.objects.filter(user=user).count()
        assert count == 0

    def test_trial_expiry_notification_created(self, user, category):
        """check_upcoming_renewals (or a trial task) creates a trial-expiry notification."""
        from apps.notifications.models import Notification
        from apps.notifications.tasks import check_expiring_trials
        from apps.subscriptions.models import Subscription

        Subscription.objects.create(
            user=user,
            name='Trial App',
            category=category,
            amount='12.00',
            billing_cycle='monthly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=5),
            is_trial=True,
            trial_end_date=date.today() + timedelta(days=5),
            status='active',
            reminder_days_before=7,
        )

        check_expiring_trials()

        notif = Notification.objects.filter(
            user=user,
            notification_type='trial_ending',
        ).first()
        assert notif is not None
