from datetime import date

import pytest
from django.core.management import call_command
from django.template import Context, Template
from django.test import Client


@pytest.mark.django_db
def test_seed_categories_is_idempotent():
    from apps.subscriptions.models import Category

    call_command('seed_categories', verbosity=0)
    first_count = Category.objects.filter(is_default=True).count()
    call_command('seed_categories', verbosity=0)

    assert first_count > 0
    assert Category.objects.filter(is_default=True).count() == first_count


@pytest.mark.django_db
def test_seed_demo_creates_valid_trial_and_is_idempotent():
    from apps.accounts.models import CustomUser
    from apps.subscriptions.models import Subscription

    call_command('seed_demo', verbosity=0)
    demo_user = CustomUser.objects.get(email='demo@subsentinel.com')
    trial = Subscription.objects.get(user=demo_user, name='Figma')

    assert trial.is_trial is True
    assert trial.status == 'active'
    assert trial.trial_end_date >= date.today()
    assert demo_user.subscriptions.count() == 15

    call_command('seed_demo', verbosity=0)
    assert CustomUser.objects.filter(email='demo@subsentinel.com').count() == 1
    assert demo_user.subscriptions.count() == 15


def test_core_template_tags_format_values_and_handle_invalid_input():
    template = Template(
        '{% load core_tags %}{{ amount|format_money:"INR" }}|'
        '{{ days|days_color }}|{% active_link "core:dashboard" %}'
    )
    rendered = template.render(Context({'amount': '1234.5', 'days': '2'}))

    assert '₹1,234.50' in rendered
    assert 'text-red-500' in rendered

    invalid_template = Template('{% load core_tags %}{{ value|days_color }}')
    assert invalid_template.render(Context({'value': 'not-a-number'})) == 'text-gray-400'


@pytest.mark.django_db
def test_health_endpoints_and_runtime_check():
    client = Client()
    assert client.get('/health/live/').status_code == 200
    ready = client.get('/health/ready/')
    assert ready.status_code == 200
    assert ready.json() == {
        'status': 'ok',
        'checks': {'database': True, 'migrations': True, 'cache': True},
    }
    call_command('check_runtime', verbosity=0)
