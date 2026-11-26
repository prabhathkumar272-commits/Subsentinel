"""Insight-generation helpers for the SubSentinel dashboard."""

from __future__ import annotations

from decimal import Decimal
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

from apps.subscriptions.models import (
    BillingCycle,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
)
from apps.subscriptions.services import calculate_yearly_total

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


# ------------------------------------------------------------------
# Duplicate detection
# ------------------------------------------------------------------


def find_duplicate_services(user: User) -> list[dict[str, Any]]:
    """Find subscriptions in the same category and currency with similar names.

    Uses :func:`difflib.SequenceMatcher` to compare names within each
    category. Pairs with a similarity ratio ≥ 0.6 are flagged.

    Args:
        user: The subscription owner.

    Returns:
        A list of dicts with keys ``sub_a``, ``sub_b``, ``similarity``,
        and ``potential_saving``.
    """
    subs = list(
        Subscription.objects.filter(user=user, status=SubscriptionStatus.ACTIVE)
        .select_related('category')
    )

    duplicates: list[dict[str, Any]] = []
    seen_pairs: set[tuple[int, int]] = set()

    for i, a in enumerate(subs):
        for b in subs[i + 1:]:
            if a.category_id and a.category_id == b.category_id and a.currency == b.currency:
                pair = (min(a.pk, b.pk), max(a.pk, b.pk))
                if pair in seen_pairs:
                    continue
                ratio = SequenceMatcher(None, a.name.lower(), b.name.lower()).ratio()
                if ratio >= 0.6:
                    seen_pairs.add(pair)
                    cheaper = min(a.monthly_cost, b.monthly_cost)
                    duplicates.append({
                        'sub_a': a,
                        'sub_b': b,
                        'similarity': round(ratio * 100),
                        'potential_saving': cheaper,
                    })

    return duplicates


# ------------------------------------------------------------------
# Price-increase detection
# ------------------------------------------------------------------


def detect_price_increases(user: User) -> list[dict[str, Any]]:
    """Compare recent payment amounts to detect price increases.

    Looks at the two most recent :class:`PaymentRecord` entries for each
    active subscription and flags when the later amount is higher.

    Args:
        user: The subscription owner.

    Returns:
        A list of dicts with keys ``subscription``, ``old_amount``,
        ``new_amount``, and ``increase``.
    """
    results: list[dict[str, Any]] = []
    subs = Subscription.objects.filter(user=user, status=SubscriptionStatus.ACTIVE)

    for sub in subs:
        payments = list(
            sub.payments.filter(
                status=PaymentStatus.CONFIRMED,
                currency=sub.currency,
            ).order_by('-date')[:2]
        )
        if len(payments) == 2:
            newer, older = payments[0], payments[1]
            if newer.amount > older.amount:
                results.append({
                    'subscription': sub,
                    'old_amount': older.amount,
                    'new_amount': newer.amount,
                    'increase': newer.amount - older.amount,
                    'currency': sub.currency,
                })

    return results


# ------------------------------------------------------------------
# Annual-savings suggestions
# ------------------------------------------------------------------


def suggest_annual_savings(user: User) -> list[dict[str, Any]]:
    """Estimate savings from switching monthly subscriptions to yearly.

    Assumes a 15–20 % discount for annual billing (uses 17.5 % average).

    Args:
        user: The subscription owner.

    Returns:
        A list of dicts with keys ``subscription``, ``current_yearly``,
        ``estimated_yearly``, and ``saving``.
    """
    discount = Decimal('0.175')
    results: list[dict[str, Any]] = []
    monthly_subs = Subscription.objects.filter(
        user=user,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
    )

    for sub in monthly_subs:
        current_yearly = sub.yearly_cost
        estimated = (current_yearly * (1 - discount)).quantize(Decimal('0.01'))
        saving = (current_yearly - estimated).quantize(Decimal('0.01'))
        if saving > 0:
            results.append({
                'subscription': sub,
                'current_yearly': current_yearly,
                'estimated_yearly': estimated,
                'saving': saving,
                'currency': sub.currency,
            })

    return results


# ------------------------------------------------------------------
# Yearly projection
# ------------------------------------------------------------------


def calculate_yearly_projection(user: User) -> Decimal:
    """Return the projected yearly spend for active subscriptions.

    Args:
        user: The subscription owner.

    Returns:
        Total projected yearly cost as a :class:`Decimal`.
    """
    return calculate_yearly_total(user)


# ------------------------------------------------------------------
# Unused / paused
# ------------------------------------------------------------------


def find_unused_subscriptions(user: User) -> list[dict[str, Any]]:
    """Return subscriptions that are currently paused (potentially unused).

    Args:
        user: The subscription owner.

    Returns:
        A list of dicts with keys ``subscription`` and ``monthly_cost``.
    """
    paused = Subscription.objects.filter(user=user, status=SubscriptionStatus.PAUSED)
    return [
        {'subscription': sub, 'monthly_cost': sub.monthly_cost}
        for sub in paused
    ]


# ------------------------------------------------------------------
# Aggregated insights
# ------------------------------------------------------------------


def get_all_insights(user: User) -> list[dict[str, Any]]:
    """Aggregate every insight type into a single list for the dashboard.

    Each dict contains keys ``type``, ``icon``, ``title``,
    ``description``, and ``saving`` (Decimal or None).

    Args:
        user: The subscription owner.

    Returns:
        A flat list of insight dicts whose monetary values retain their currency.
    """
    insights: list[dict[str, Any]] = []

    # Duplicates
    for dup in find_duplicate_services(user):
        insights.append({
            'type': 'duplicate',
            'icon': '🔄',
            'title': 'Possible duplicate',
            'description': (
                f'"{dup["sub_a"].name}" and "{dup["sub_b"].name}" look similar '
                f'({dup["similarity"]}% match). Consider keeping just one.'
            ),
            'saving': dup['potential_saving'],
            'currency': dup['sub_a'].currency,
        })

    # Price increases
    for inc in detect_price_increases(user):
        insights.append({
            'type': 'price_increase',
            'icon': '📈',
            'title': 'Price increase detected',
            'description': (
                f'"{inc["subscription"].name}" went from '
                f'{inc["currency"]} {inc["old_amount"]} to {inc["currency"]} {inc["new_amount"]} '
                f'(+{inc["currency"]} {inc["increase"]}).'
            ),
            'saving': None,
            'currency': inc['currency'],
        })

    # Annual-plan savings
    for sav in suggest_annual_savings(user):
        insights.append({
            'type': 'annual_saving',
            'icon': '💡',
            'title': 'Switch to annual',
            'description': (
                f'Switching "{sav["subscription"].name}" to yearly billing '
                f'could save ~{sav["currency"]} {sav["saving"]}/year.'
            ),
            'saving': sav['saving'],
            'currency': sav['currency'],
        })

    # Unused
    for unused in find_unused_subscriptions(user):
        insights.append({
            'type': 'unused',
            'icon': '⏸️',
            'title': 'Paused subscription',
            'description': (
                f'"{unused["subscription"].name}" is paused. '
                f'Cancel to save {unused["subscription"].currency} {unused["monthly_cost"]}/mo.'
            ),
            'saving': unused['monthly_cost'],
            'currency': unused['subscription'].currency,
        })

    # Amounts in distinct currencies are not comparable, so preserve the
    # insight groups instead of sorting mixed monetary values.
    return insights
