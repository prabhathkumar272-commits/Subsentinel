import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone


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


@login_required
def dashboard(request):
    # Import services
    from apps.insights.services import get_all_insights
    from apps.subscriptions.models import PaymentRecord
    from apps.subscriptions.services import (
        calculate_monthly_total,
        calculate_yearly_total,
        get_expiring_trials,
        get_upcoming_renewals,
        get_user_subscriptions,
    )

    user = request.user

    # ── Summary metrics ────────────────────────────────────────────────────────
    monthly_total = calculate_monthly_total(user)
    yearly_total = calculate_yearly_total(user)
    active_subs = get_user_subscriptions(user).filter(status='active')
    active_count = active_subs.count()

    # Next renewal
    upcoming = get_upcoming_renewals(user, days=365).first()
    next_renewal_date = upcoming.next_billing_date if upcoming else None
    next_renewal_name = upcoming.name if upcoming else None

    # ── Category chart data (donut) ────────────────────────────────────────────
    from django.db.models import Sum

    category_data = {}
    for sub in active_subs.select_related('category'):
        cat_name = sub.category.name if sub.category else 'Other'
        cat_color = sub.category.color if sub.category else '#78909C'
        if cat_name not in category_data:
            category_data[cat_name] = {'total': Decimal('0'), 'color': cat_color}
        category_data[cat_name]['total'] += sub.monthly_cost

    # ── Monthly spend trend (last 12 months) ───────────────────────────────────
    from datetime import date
    today = date.today()
    monthly_trend = []
    trend_labels = []
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - timezone.timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)
        total = (
            PaymentRecord.objects.filter(
                subscription__user=user,
                date__gte=month_start,
                date__lt=month_end,
            ).aggregate(Sum('amount'))['amount__sum']
            or Decimal('0')
        )
        monthly_trend.append(float(total))
        trend_labels.append(month_start.strftime('%b %Y'))

    # ── Top 5 most expensive ───────────────────────────────────────────────────
    top_subs = sorted(active_subs, key=lambda s: s.monthly_cost, reverse=True)[:5]

    # ── Upcoming renewals (next 30 days) ───────────────────────────────────────
    upcoming_30 = get_upcoming_renewals(user, days=30)

    chart_data = {
        'categories': {
            'labels': list(category_data.keys()),
            'data': [float(v['total']) for v in category_data.values()],
            'colors': [v['color'] for v in category_data.values()],
        },
        'trend': {
            'labels': trend_labels,
            'data': monthly_trend,
        },
        'renewals': {
            'labels': [s.name for s in upcoming_30[:10]],
            'data': [float(s.monthly_cost) for s in upcoming_30[:10]],
            'dates': [s.next_billing_date.strftime('%b %d') for s in upcoming_30[:10]],
        },
        'topExpensive': {
            'labels': [s.name for s in top_subs],
            'data': [float(s.monthly_cost) for s in top_subs],
            'colors': [s.category.color if s.category else '#6366F1' for s in top_subs],
        },
    }

    insights = get_all_insights(user)
    expiring_trials = get_expiring_trials(user, days=14)

    context = {
        'monthly_total': monthly_total,
        'yearly_total': yearly_total,
        'active_count': active_count,
        'next_renewal_date': next_renewal_date,
        'next_renewal_name': next_renewal_name,
        'chart_data': json.dumps(chart_data, default=str),
        'insights': insights,
        'upcoming_renewals': upcoming_30[:8],
        'expiring_trials': expiring_trials,
    }
    return render(request, 'core/dashboard.html', context)
