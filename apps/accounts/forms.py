from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import UserSettings

User = get_user_model()

TAILWIND_INPUT = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-white '
    'text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 '
    'focus:border-indigo-500 transition-colors'
)

TAILWIND_CHECKBOX = 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'

TAILWIND_SELECT = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-white '
    'text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors'
)


class CustomRegistrationForm(UserCreationForm):
    """Registration form using email instead of username."""

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': TAILWIND_INPUT,
                'placeholder': 'you@example.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT,
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT,
                'placeholder': 'Last name',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': TAILWIND_INPUT,
            'placeholder': 'Password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': TAILWIND_INPUT,
            'placeholder': 'Confirm password',
        })


class LoginForm(AuthenticationForm):
    """Login form with email as the identifier."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'
        self.fields['username'].widget = forms.EmailInput(attrs={
            'class': TAILWIND_INPUT,
            'placeholder': 'you@example.com',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': TAILWIND_INPUT,
            'placeholder': 'Password',
        })


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile details."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT,
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT,
                'placeholder': 'Last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': TAILWIND_INPUT,
                'placeholder': 'you@example.com',
            }),
        }


class UserSettingsForm(forms.ModelForm):
    """Form for editing user preferences."""

    class Meta:
        model = UserSettings
        fields = ('default_currency', 'default_reminder_days', 'email_reminders_enabled', 'theme')
        widgets = {
            'default_currency': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'default_reminder_days': forms.NumberInput(attrs={
                'class': TAILWIND_INPUT,
                'min': '0',
                'max': '30',
            }),
            'email_reminders_enabled': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX}),
            'theme': forms.Select(attrs={'class': TAILWIND_SELECT}),
        }
