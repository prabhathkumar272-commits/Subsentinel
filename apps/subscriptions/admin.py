from django.contrib import admin

from apps.subscriptions.models import Category, PaymentRecord, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for Subscription."""

    list_display = (
        'name', 'user', 'amount', 'currency', 'billing_cycle',
        'status', 'next_billing_date', 'category',
    )
    list_filter = ('status', 'billing_cycle', 'currency', 'category')
    search_fields = ('name', 'user__email', 'notes')
    date_hierarchy = 'next_billing_date'
    raw_id_fields = ('user',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category."""

    list_display = ('name', 'color', 'icon', 'is_default', 'user')
    list_filter = ('is_default',)
    search_fields = ('name',)


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentRecord."""

    list_display = ('subscription', 'amount', 'currency', 'status', 'date', 'confirmed_at')
    list_filter = ('status', 'currency', 'date')
    search_fields = ('subscription__name',)
    date_hierarchy = 'date'
    raw_id_fields = ('subscription',)
