import os

import pytest

# Ensure Django settings are configured before any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')


@pytest.fixture
def user(db):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        email='test@test.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
    )


@pytest.fixture
def other_user(db):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        email='other@test.com',
        password='testpass123',
    )


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def category(db):
    from apps.subscriptions.models import Category
    return Category.objects.create(
        name='Entertainment',
        color='#EF4444',
        icon='🎬',
        is_default=True,
    )


@pytest.fixture
def subscription(db, user, category):
    from datetime import date, timedelta
    from decimal import Decimal

    from apps.subscriptions.models import Subscription
    return Subscription.objects.create(
        user=user,
        name='Netflix',
        category=category,
        amount=Decimal('15.99'),
        billing_cycle='monthly',
        start_date=date.today() - timedelta(days=90),
        next_billing_date=date.today() + timedelta(days=5),
        status='active',
    )
