from django import forms

from apps.subscriptions.models import Category, Subscription, SubscriptionStatus

TAILWIND_INPUT = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-white '
    'text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 '
    'focus:border-indigo-500 transition-colors'
)

TAILWIND_SELECT = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-white '
    'text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors'
)

TAILWIND_TEXTAREA = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-white '
    'text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 '
    'focus:border-indigo-500 transition-colors resize-y'
)

TAILWIND_CHECKBOX = 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'


class SubscriptionForm(forms.ModelForm):
    """Form for creating and editing subscriptions."""

    class Meta:
        model = Subscription
        fields = (
            'name', 'category', 'amount', 'currency', 'billing_cycle', 'start_date',
            'next_billing_date', 'is_trial', 'trial_end_date', 'status',
            'reminder_days_before', 'payment_method', 'website_url', 'notes', 'logo_url',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'e.g. Netflix'}),
            'category': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'amount': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'step': '0.01', 'min': '0.01'}),
            'currency': forms.Select(
                attrs={'class': TAILWIND_SELECT},
                choices=[
                    ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'),
                    ('INR', 'INR'), ('CAD', 'CAD'), ('AUD', 'AUD'), ('JPY', 'JPY'),
                ],
            ),
            'billing_cycle': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'start_date': forms.DateInput(attrs={'class': TAILWIND_INPUT, 'type': 'date'}),
            'next_billing_date': forms.DateInput(attrs={'class': TAILWIND_INPUT, 'type': 'date'}),
            'is_trial': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX}),
            'trial_end_date': forms.DateInput(attrs={'class': TAILWIND_INPUT, 'type': 'date'}),
            'status': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'reminder_days_before': forms.NumberInput(attrs={'class': TAILWIND_INPUT, 'min': '0', 'max': '30'}),
            'payment_method': forms.TextInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'e.g. Visa ****1234'}),
            'website_url': forms.URLInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'https://...'}),
            'notes': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Optional notes'}),
            'logo_url': forms.URLInput(attrs={'class': TAILWIND_INPUT, 'placeholder': 'https://logo.clearbit.com/...'}),
        }


class SubscriptionFilterForm(forms.Form):
    """Filter and sort controls for the subscription list."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT,
            'placeholder': 'Search subscriptions…',
        }),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(SubscriptionStatus.choices),
        widget=forms.Select(attrs={'class': TAILWIND_SELECT}),
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('name', 'Name A–Z'),
            ('-amount', 'Price High–Low'),
            ('next_billing_date', 'Next Billing ↑'),
            ('-next_billing_date', 'Next Billing ↓'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT}),
    )
