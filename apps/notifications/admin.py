from django.contrib import admin

from apps.notifications.models import Notification, ReminderLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification."""

    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user', 'related_subscription')


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    """Admin configuration for ReminderLog."""

    list_display = ('subscription', 'reminder_type', 'reminder_date', 'sent_at')
    list_filter = ('reminder_type',)
    search_fields = ('subscription__name',)
    date_hierarchy = 'reminder_date'
    raw_id_fields = ('subscription',)
