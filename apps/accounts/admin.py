from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import CustomUser, UserSettings


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the custom user model."""

    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for user settings."""

    list_display = ('user', 'default_currency', 'default_reminder_days', 'email_reminders_enabled', 'theme')
    list_filter = ('default_currency', 'theme', 'email_reminders_enabled')
    search_fields = ('user__email',)
