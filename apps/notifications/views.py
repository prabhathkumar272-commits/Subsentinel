from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.notifications.models import Notification


@login_required
def notification_dropdown(request):
    """Return the latest unread notifications as an HTMX partial."""
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False,
    )[:5]
    return render(request, 'notifications/dropdown.html', {
        'notifications': notifications,
    })


@login_required
def notification_list(request):
    """Full-page notification list."""
    notifications = Notification.objects.filter(user=request.user)
    return render(request, 'notifications/list.html', {
        'notifications': notifications,
    })


@login_required
def mark_read(request, pk: int):
    """Mark a single notification as read (HTMX)."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    if request.headers.get('HX-Request'):
        return render(request, 'notifications/partials/notification_item.html', {
            'notification': notification,
        })
    return render(request, 'notifications/list.html', {
        'notifications': Notification.objects.filter(user=request.user),
    })


@login_required
def mark_all_read(request):
    """Mark all notifications as read (HTMX)."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    if request.headers.get('HX-Request'):
        return HttpResponse('<span class="text-sm text-gray-500">All caught up!</span>')
    return render(request, 'notifications/list.html', {
        'notifications': Notification.objects.filter(user=request.user),
    })


@login_required
def unread_count(request):
    """Return the unread notification count for a badge (HTMX polling)."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    if count > 0:
        return HttpResponse(
            f'<span class="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center '
            f'rounded-full bg-red-500 text-xs text-white">{count}</span>'
        )
    return HttpResponse('')
