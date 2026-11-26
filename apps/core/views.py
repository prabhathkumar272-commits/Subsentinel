import json
import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

logger = logging.getLogger(__name__)


def handler400(request, exception=None):
    return render(request, 'errors/404.html', {'code': 400, 'message': 'Bad Request'}, status=400)


def handler403(request, exception=None):
    return render(request, 'errors/404.html', {'code': 403, 'message': 'Permission Denied'}, status=403)


def handler404(request, exception=None):
    return render(request, 'errors/404.html', {'code': 404, 'message': 'Page Not Found'}, status=404)


def handler500(request):
    return render(request, 'errors/500.html', {'code': 500, 'message': 'Server Error'}, status=500)


def landing(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/landing.html')


def health_live(request):
    """Liveness probe: the Django process can serve requests."""
    return JsonResponse({'status': 'ok'})


def health_ready(request):
    """Readiness probe: database and configured cache are responding."""
    checks = {'database': False, 'migrations': False, 'cache': False}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = True
        executor = MigrationExecutor(connection)
        checks['migrations'] = not executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        logger.warning('Database readiness probe failed', exc_info=True)

    probe_key = 'subsentinel:readiness-probe'
    try:
        cache.set(probe_key, 'ok', timeout=5)
        checks['cache'] = cache.get(probe_key) == 'ok'
    except Exception:
        logger.warning('Cache readiness probe failed', exc_info=True)

    ready = all(checks.values())
    return JsonResponse(
        {'status': 'ok' if ready else 'unavailable', 'checks': checks},
        status=200 if ready else 503,
    )


@login_required
def dashboard(request):
    # Import services
    from apps.insights.services import get_all_insights
    from apps.subscriptions.models import PaymentRecord, PaymentStatus
    from apps.subscriptions.services import (
        calculate_monthly_total,
        calculate_totals_by_currency,
        calculate_yearly_total,
        get_expiring_trials,
        get_upcoming_renewals,
        get_user_subscriptions,
    )

    user = request.user
    display_currency = user.settings.default_currency

    # ── Summary metrics ────────────────────────────────────────────────────────
    currency_totals = calculate_totals_by_currency(user)
    monthly_total = calculate_monthly_total(user)
    yearly_total = calculate_yearly_total(user)
    active_subs = get_user_subscriptions(user).filter(status='active')
    chart_subs = active_subs.filter(currency=display_currency)
    active_count = active_subs.count()

    # Next renewal
    upcoming = get_upcoming_renewals(user, days=365).first()
    next_renewal_date = upcoming.next_billing_date if upcoming else None
    next_renewal_name = upcoming.name if upcoming else None

    # ── Category chart data (donut) ────────────────────────────────────────────
    from django.db.models import Sum

    category_data = {}
    for sub in chart_subs.select_related('category'):
        cat_name = sub.category.name if sub.category else 'Other'
        cat_color = sub.category.color if sub.category else '#78909C'
        if cat_name not in category_data:
            category_data[cat_name] = {'total': Decimal('0'), 'color': cat_color}
        category_data[cat_name]['total'] += sub.monthly_cost

    # ── Monthly spend trend (last 12 months) ───────────────────────────────────
    from datetime import date
    today = timezone.localdate()
    monthly_trend = []
    trend_labels = []
    for i in range(11, -1, -1):
        month_index = today.year * 12 + today.month - 1 - i
        month_year, month_zero_indexed = divmod(month_index, 12)
        month_start = date(month_year, month_zero_indexed + 1, 1)
        if month_zero_indexed == 11:
            month_end = date(month_year + 1, 1, 1)
        else:
            month_end = date(month_year, month_zero_indexed + 2, 1)
        total = (
            PaymentRecord.objects.filter(
                subscription__user=user,
                status=PaymentStatus.CONFIRMED,
                currency=display_currency,
                date__gte=month_start,
                date__lt=month_end,
            ).aggregate(Sum('amount'))['amount__sum']
            or Decimal('0')
        )
        monthly_trend.append(float(total))
        trend_labels.append(month_start.strftime('%b %Y'))

    # ── Top 5 most expensive ───────────────────────────────────────────────────
    top_subs = sorted(chart_subs, key=lambda s: s.monthly_cost, reverse=True)[:5]

    # ── Upcoming renewals (next 30 days) ───────────────────────────────────────
    upcoming_30 = get_upcoming_renewals(user, days=30)
    chart_renewals = upcoming_30.filter(currency=display_currency)

    chart_data = {
        'currency': display_currency,
        'category_labels': list(category_data.keys()),
        'category_amounts': [float(value['total']) for value in category_data.values()],
        'category_colors': [value['color'] for value in category_data.values()],
        'trend_labels': trend_labels,
        'trend_amounts': monthly_trend,
        'renewal_labels': [sub.name for sub in chart_renewals[:10]],
        'renewal_amounts': [float(sub.monthly_cost) for sub in chart_renewals[:10]],
        'renewal_days': [sub.days_until_billing for sub in chart_renewals[:10]],
        'top_labels': [sub.name for sub in top_subs],
        'top_amounts': [float(sub.monthly_cost) for sub in top_subs],
        'top_colors': [sub.category.color if sub.category else '#62734B' for sub in top_subs],
    }

    insights = get_all_insights(user)
    expiring_trials = get_expiring_trials(user, days=14)

    context = {
        'monthly_total': monthly_total,
        'yearly_total': yearly_total,
        'currency_totals': currency_totals,
        'display_currency': display_currency,
        'active_count': active_count,
        'next_renewal_date': next_renewal_date,
        'next_renewal_name': next_renewal_name,
        'chart_data': json.dumps(chart_data, default=str),
        'insights': insights,
        'upcoming_renewals': upcoming_30[:8],
        'expiring_trials': expiring_trials,
    }
    return render(request, 'core/dashboard.html', context)
