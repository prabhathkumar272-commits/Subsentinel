from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.subscriptions.forms import SubscriptionFilterForm, SubscriptionForm
from apps.subscriptions.models import PaymentRecord, PaymentStatus, Subscription, SubscriptionStatus
from apps.subscriptions.services import (
    export_subscriptions_csv,
    export_subscriptions_pdf,
    get_user_subscriptions,
)


@login_required
def subscription_list(request):
    """List subscriptions with filtering, search, sorting, and pagination."""
    filter_form = SubscriptionFilterForm(request.GET or None)
    filters = {}

    if filter_form.is_valid():
        filters = {
            'search': filter_form.cleaned_data.get('search'),
            'category': (
                filter_form.cleaned_data['category'].pk
                if filter_form.cleaned_data.get('category')
                else None
            ),
            'status': filter_form.cleaned_data.get('status'),
            'sort_by': filter_form.cleaned_data.get('sort_by'),
        }

    subscriptions = get_user_subscriptions(request.user, filters)
    paginator = Paginator(subscriptions, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    view_mode = request.GET.get('view', 'card')

    return render(request, 'subscriptions/list.html', {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'view_mode': view_mode,
    })


@login_required
def subscription_create(request):
    """Create a new subscription."""
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f'"{subscription.name}" has been added.')
            return redirect('subscriptions:detail', pk=subscription.pk)
    else:
        form = SubscriptionForm(initial={'currency': request.user.settings.default_currency})

    return render(request, 'subscriptions/create.html', {'form': form})


@login_required
def subscription_detail(request, pk: int):
    """Display a single subscription's details."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    return render(request, 'subscriptions/detail.html', {'subscription': subscription})


@login_required
@require_POST
def confirm_payment(request, pk: int):
    """Confirm an expected renewal after the user verifies the charge."""
    record = get_object_or_404(PaymentRecord, pk=pk, subscription__user=request.user)
    if record.status == PaymentStatus.EXPECTED:
        record.status = PaymentStatus.CONFIRMED
        record.confirmed_at = timezone.now()
        record.save(update_fields=['status', 'confirmed_at'])
        messages.success(request, f'{record.subscription.name} renewal marked as paid.')
    else:
        messages.info(request, 'This renewal was already confirmed.')
    return redirect('subscriptions:detail', pk=record.subscription_id)


@login_required
def subscription_edit(request, pk: int):
    """Edit an existing subscription."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)

    if request.method == 'POST':
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{subscription.name}" has been updated.')
            return redirect('subscriptions:detail', pk=subscription.pk)
    else:
        form = SubscriptionForm(instance=subscription)

    return render(request, 'subscriptions/edit.html', {'form': form, 'subscription': subscription})


@login_required
def subscription_delete(request, pk: int):
    """Delete a subscription (POST only)."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)

    if request.method == 'POST':
        name = subscription.name
        subscription.delete()
        messages.success(request, f'"{name}" has been deleted.')
        return redirect('subscriptions:list')

    return render(request, 'subscriptions/confirm_delete.html', {'subscription': subscription})


# ------------------------------------------------------------------
# HTMX status toggles
# ------------------------------------------------------------------

@login_required
def subscription_pause(request, pk: int):
    """Pause an active subscription (HTMX)."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    subscription.status = SubscriptionStatus.PAUSED
    subscription.save(update_fields=['status'])
    messages.success(request, f'"{subscription.name}" has been paused.')

    if request.headers.get('HX-Request'):
        return render(request, 'subscriptions/partials/status_badge.html', {'subscription': subscription})
    return redirect('subscriptions:detail', pk=pk)


@login_required
def subscription_resume(request, pk: int):
    """Resume a paused subscription (HTMX)."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.save(update_fields=['status'])
    messages.success(request, f'"{subscription.name}" has been resumed.')

    if request.headers.get('HX-Request'):
        return render(request, 'subscriptions/partials/status_badge.html', {'subscription': subscription})
    return redirect('subscriptions:detail', pk=pk)


@login_required
def subscription_cancel(request, pk: int):
    """Cancel a subscription (HTMX)."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.save(update_fields=['status'])
    messages.success(request, f'"{subscription.name}" has been cancelled.')

    if request.headers.get('HX-Request'):
        return render(request, 'subscriptions/partials/status_badge.html', {'subscription': subscription})
    return redirect('subscriptions:detail', pk=pk)


@login_required
def export_csv(request) -> HttpResponse:
    """Export the user's subscriptions as a CSV download."""
    return export_subscriptions_csv(request.user)


@login_required
def export_pdf(request) -> HttpResponse:
    """Export the user's subscriptions as a printable PDF report."""
    return export_subscriptions_pdf(request.user)
