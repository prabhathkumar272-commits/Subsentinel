from django import template
from django.utils.html import format_html

from apps.subscriptions.models import BillingCycle, SubscriptionStatus

register = template.Library()


@register.simple_tag
def trial_badge(subscription) -> str:
    """Render a small badge if the subscription is a trial."""
    if not subscription.is_trial:
        return ''
    remaining = subscription.trial_days_remaining
    if remaining is not None and remaining <= 3:
        colour = 'bg-red-100 text-red-700'
    else:
        colour = 'bg-yellow-100 text-yellow-700'
    label = f'{remaining}d left' if remaining is not None else 'Trial'
    return format_html(
        '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {}">{}</span>',
        colour,
        label,
    )


@register.simple_tag
def status_badge(subscription) -> str:
    """Render a colour-coded status badge."""
    colours = {
        SubscriptionStatus.ACTIVE: 'bg-green-100 text-green-700',
        SubscriptionStatus.PAUSED: 'bg-yellow-100 text-yellow-700',
        SubscriptionStatus.CANCELLED: 'bg-red-100 text-red-700',
    }
    colour = colours.get(subscription.status, 'bg-gray-100 text-gray-700')
    label = subscription.get_status_display()
    return format_html(
        '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {}">{}</span>',
        colour,
        label,
    )


@register.filter
def format_billing_cycle(value: str) -> str:
    """Human-readable billing-cycle label."""
    labels = {
        BillingCycle.WEEKLY: 'Weekly',
        BillingCycle.MONTHLY: 'Monthly',
        BillingCycle.QUARTERLY: 'Quarterly',
        BillingCycle.YEARLY: 'Yearly',
    }
    return labels.get(value, value)


@register.filter
def format_currency(amount, currency: str = 'USD') -> str:
    """Format *amount* with a currency symbol."""
    symbols = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'INR': '₹',
        'CAD': 'CA$', 'AUD': 'A$', 'JPY': '¥',
    }
    symbol = symbols.get(currency, currency + ' ')
    try:
        return f'{symbol}{amount:,.2f}'
    except (TypeError, ValueError):
        return f'{symbol}{amount}'
