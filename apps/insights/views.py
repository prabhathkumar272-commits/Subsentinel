import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.subscriptions.models import Subscription, SubscriptionStatus


@login_required
def calendar_view(request):
    """Render a monthly calendar grid with subscription renewal dates."""
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    # Gather renewals for the requested month
    subs = Subscription.objects.filter(
        user=request.user,
        status=SubscriptionStatus.ACTIVE,
        next_billing_date__year=year,
        next_billing_date__month=month,
    ).select_related('category')

    renewals_by_day: dict[int, list] = {}
    for sub in subs:
        day = sub.next_billing_date.day
        renewals_by_day.setdefault(day, []).append(sub)

    # Build weeks data for the template
    weeks = []
    for week in month_days:
        week_data = []
        for day in week:
            week_data.append({
                'day': day,
                'is_today': (day == today.day and month == today.month and year == today.year),
                'renewals': renewals_by_day.get(day, []),
            })
        weeks.append(week_data)

    # Navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return render(request, 'insights/calendar.html', {
        'weeks': weeks,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'today': today,
    })
