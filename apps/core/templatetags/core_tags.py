from decimal import Decimal

from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.filter
def format_money(value, currency='USD'):
    """Format a decimal/float as a currency string, e.g. $15.99."""
    try:
        amount = Decimal(str(value))
    except Exception:
        return value
    symbols = {
        'USD': '$', 'EUR': '€', 'GBP': '£',
        'CAD': 'CA$', 'AUD': 'A$', 'INR': '₹', 'JPY': '¥',
    }
    formatted = f'{amount:,.2f}'
    symbol = symbols.get(currency)
    return f'{symbol}{formatted}' if symbol else f'{currency} {formatted}'


@register.filter
def days_color(days):
    """Return a Tailwind CSS text-color class based on days remaining.

    ≤ 3  → red-500 (urgent)
    ≤ 7  → orange-500 (warning)
    ≤ 14 → yellow-500 (caution)
    else → green-600 (safe)
    """
    try:
        days = int(days)
    except (TypeError, ValueError):
        return 'text-gray-400'

    if days <= 3:
        return 'text-red-500'
    elif days <= 7:
        return 'text-orange-500'
    elif days <= 14:
        return 'text-yellow-500'
    return 'text-green-600'


@register.simple_tag(takes_context=True)
def active_link(context, url_name, css_class='active'):
    """Return *css_class* when the current URL matches the named URL.

    Usage:
        <a class="{% active_link request 'core:dashboard' %}">Dashboard</a>
    """
    request = context.get('request')
    if request is None:
        return ''
    try:
        url = reverse(url_name)
    except NoReverseMatch:
        return ''
    return css_class if request.path == url else ''
