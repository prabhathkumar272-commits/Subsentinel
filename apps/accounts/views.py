from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.forms import (
    CustomRegistrationForm,
    UserProfileForm,
    UserSettingsForm,
)


def register(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Welcome to SubSentinel! Your account has been created.')
            return redirect('core:dashboard')
    else:
        form = CustomRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_settings(request):
    """Display and handle updates to the user profile and settings."""
    user = request.user
    user_settings = user.settings

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=user)
        settings_form = UserSettingsForm(request.POST, instance=user_settings)

        if profile_form.is_valid() and settings_form.is_valid():
            profile_form.save()
            settings_form.save()
            messages.success(request, 'Your profile and settings have been updated.')
            return redirect('accounts:profile')
    else:
        profile_form = UserProfileForm(instance=user)
        settings_form = UserSettingsForm(instance=user_settings)

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'settings_form': settings_form,
    })


@login_required
def delete_account(request):
    """Delete the authenticated user's account on POST."""
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.info(request, 'Your account has been permanently deleted.')
        return redirect('core:landing')
    return redirect('accounts:profile')
