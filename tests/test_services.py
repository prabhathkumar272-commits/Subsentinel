from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Import / detection services
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDetectRecurring:
    def _make_df(self, rows):
        return pd.DataFrame(rows, columns=['date', 'description', 'amount'])

    def test_detect_monthly_recurring(self):
        from apps.imports.services import detect_recurring

        rows = []
        for i in range(4):
            d = date(2024, 1, 1) + timedelta(days=30 * i)
            rows.append({'date': d, 'description': 'NETFLIX.COM', 'amount': -15.99})
        rows.extend([
            {'date': date(2024, 1, 5), 'description': 'WALMART', 'amount': -52.30},
            {'date': date(2024, 2, 7), 'description': 'SHELL OIL', 'amount': -45.00},
        ])
        df = pd.DataFrame(rows)
        results = detect_recurring(df)
        merchants = [r['normalized_name'] for r in results]
        assert any('netflix' in m for m in merchants)

    def test_normalize_merchant_strips_noise(self):
        from apps.imports.services import normalize_merchant

        n1 = normalize_merchant('POS DEBIT NETFLIX.COM 866-579')
        n2 = normalize_merchant('NETFLIX SUBSCRIPTION')
        # Both should normalize to something containing 'netflix'
        assert 'netflix' in n1
        assert 'netflix' in n2

    def test_non_recurring_not_detected(self):
        from apps.imports.services import detect_recurring

        rows = [
            {'date': date(2024, 1, 5),  'description': 'WALMART',  'amount': -52.30},
            {'date': date(2024, 1, 15), 'description': 'TARGET',   'amount': -34.50},
            {'date': date(2024, 2, 3),  'description': 'MCDONALDS','amount': -8.75},
        ]
        df = pd.DataFrame(rows)
        results = detect_recurring(df)
        assert len(results) == 0

    def test_detect_requires_minimum_occurrences(self):
        """A transaction appearing only twice should NOT be flagged as recurring."""
        from apps.imports.services import detect_recurring

        rows = [
            {'date': date(2024, 1, 10), 'description': 'SOME SERVICE', 'amount': -9.99},
            {'date': date(2024, 2, 10), 'description': 'SOME SERVICE', 'amount': -9.99},
        ]
        df = pd.DataFrame(rows)
        results = detect_recurring(df)
        # 2 occurrences is typically below the threshold (3+)
        assert len(results) == 0

    def test_detect_multiple_merchants(self):
        from apps.imports.services import detect_recurring

        rows = []
        for i in range(4):
            d = date(2024, 1, 1) + timedelta(days=30 * i)
            rows.append({'date': d, 'description': 'SPOTIFY PREMIUM', 'amount': -9.99})
            rows.append({'date': d, 'description': 'ADOBE CREATIVE', 'amount': -54.99})
        df = pd.DataFrame(rows)
        results = detect_recurring(df)
        names = [r['normalized_name'] for r in results]
        assert any('spotify' in n for n in names)
        assert any('adobe' in n for n in names)


# ─────────────────────────────────────────────────────────────────────────────
# Subscription services
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSubscriptionServices:
    def test_calculate_monthly_total(self, user, subscription):
        from apps.subscriptions.services import calculate_monthly_total
        total = calculate_monthly_total(user)
        assert total >= Decimal('15.99')

    def test_calculate_yearly_total(self, user, subscription):
        from apps.subscriptions.services import calculate_yearly_total
        total = calculate_yearly_total(user)
        assert total >= Decimal('15.99') * 12

    def test_get_upcoming_renewals(self, user, subscription):
        from apps.subscriptions.services import get_upcoming_renewals
        renewals = get_upcoming_renewals(user, days=30)
        assert subscription in renewals

    def test_get_upcoming_renewals_excludes_far_future(self, user, category):
        from datetime import date, timedelta

        from apps.subscriptions.models import Subscription
        from apps.subscriptions.services import get_upcoming_renewals

        far_sub = Subscription.objects.create(
            user=user,
            name='Far Future',
            category=category,
            amount='9.99',
            billing_cycle='monthly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=60),
            status='active',
        )
        renewals = get_upcoming_renewals(user, days=30)
        assert far_sub not in renewals

    def test_get_expiring_trials(self, user, category):
        from datetime import date, timedelta

        from apps.subscriptions.models import Subscription
        from apps.subscriptions.services import get_expiring_trials

        trial_sub = Subscription.objects.create(
            user=user,
            name='Trial Service',
            category=category,
            amount='12.00',
            billing_cycle='monthly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=10),
            trial_end_date=date.today() + timedelta(days=10),
            status='trial',
        )
        expiring = get_expiring_trials(user, days=14)
        assert trial_sub in expiring
