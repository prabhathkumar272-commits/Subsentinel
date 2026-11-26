from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

# ─────────────────────────────────────────────────────────────────────────────
# CustomUser
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCustomUser:
    def test_create_user_with_email(self):
        from apps.accounts.models import CustomUser
        user = CustomUser.objects.create_user(email='a@b.com', password='pass123')
        assert user.email == 'a@b.com'
        assert user.check_password('pass123')

    def test_user_requires_email(self):
        from apps.accounts.models import CustomUser
        with pytest.raises(ValueError):
            CustomUser.objects.create_user(email='', password='pass')

    def test_user_str_contains_email(self):
        from apps.accounts.models import CustomUser
        user = CustomUser.objects.create_user(email='str@test.com', password='pass')
        assert 'str@test.com' in str(user)

    def test_user_settings_auto_created(self, user):
        """UserSettings should be created via post_save signal."""
        assert hasattr(user, 'settings')
        assert user.settings is not None

    def test_superuser_creation(self):
        from apps.accounts.models import CustomUser
        su = CustomUser.objects.create_superuser(email='admin@test.com', password='adminpass')
        assert su.is_staff
        assert su.is_superuser


# ─────────────────────────────────────────────────────────────────────────────
# Subscription
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSubscription:
    def test_monthly_cost_monthly(self, subscription):
        assert subscription.monthly_cost == subscription.amount

    def test_yearly_cost(self, subscription):
        assert subscription.yearly_cost == subscription.amount * 12

    def test_monthly_cost_yearly(self, user, category):
        from apps.subscriptions.models import Subscription
        sub = Subscription.objects.create(
            user=user,
            name='Annual Plan',
            category=category,
            amount='99.99',
            billing_cycle='yearly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=365),
        )
        assert round(sub.monthly_cost, 2) == round(Decimal('99.99') / 12, 2)

    def test_days_until_billing(self, subscription):
        # subscription fixture is due in 5 days
        assert 4 <= subscription.days_until_billing <= 6

    def test_subscription_str(self, subscription):
        assert 'Netflix' in str(subscription)

    def test_status_default_active(self, user, category):
        from apps.subscriptions.models import Subscription
        sub = Subscription.objects.create(
            user=user,
            name='Test',
            category=category,
            amount='5.00',
            billing_cycle='monthly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=30),
        )
        assert sub.status == 'active'

    def test_weekly_monthly_cost(self, user, category):
        from apps.subscriptions.models import Subscription
        sub = Subscription.objects.create(
            user=user,
            name='Weekly',
            category=category,
            amount='2.99',
            billing_cycle='weekly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=7),
        )
        # weekly × 52 / 12 ≈ 12.96
        assert sub.monthly_cost > Decimal('10')


# ─────────────────────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategory:
    def test_category_str(self, category):
        assert 'Entertainment' in str(category)

    def test_default_category_flag(self, category):
        assert category.is_default is True


@pytest.mark.django_db
def test_expected_renewal_has_database_idempotency_guard(subscription):
    from apps.subscriptions.models import PaymentRecord, PaymentStatus

    PaymentRecord.objects.create(
        subscription=subscription,
        amount=subscription.amount,
        date=subscription.next_billing_date,
        status=PaymentStatus.EXPECTED,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentRecord.objects.create(
            subscription=subscription,
            amount=subscription.amount,
            date=subscription.next_billing_date,
            status=PaymentStatus.EXPECTED,
        )
