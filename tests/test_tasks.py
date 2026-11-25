from datetime import date, timedelta

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
