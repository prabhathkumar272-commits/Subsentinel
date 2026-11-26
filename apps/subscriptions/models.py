from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class BillingCycle(models.TextChoices):
    WEEKLY = 'weekly', 'Weekly'
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    YEARLY = 'yearly', 'Yearly'


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    CANCELLED = 'cancelled', 'Cancelled'


class Category(models.Model):
    """Subscription category with an icon and colour swatch."""

    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#6366F1')
    icon = models.CharField(max_length=50, default='📦')
    is_default = models.BooleanField(default=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categories',
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self) -> str:
        return self.name


class Subscription(models.Model):
    """A single recurring subscription tracked by the user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices)
    start_date = models.DateField()
    next_billing_date = models.DateField()
    is_trial = models.BooleanField(default=False)
    trial_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
    )
    reminder_days_before = models.PositiveIntegerField(default=3)
    payment_method = models.CharField(max_length=100, blank=True)
    website_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['next_billing_date']),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.get_billing_cycle_display()})'

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def monthly_cost(self) -> Decimal:
        """Return the equivalent monthly cost of this subscription."""
        cycle_map = {
            BillingCycle.WEEKLY: Decimal('4.33'),
            BillingCycle.MONTHLY: Decimal('1'),
            BillingCycle.QUARTERLY: Decimal('1') / Decimal('3'),
            BillingCycle.YEARLY: Decimal('1') / Decimal('12'),
        }
        multiplier = cycle_map.get(self.billing_cycle, Decimal('1'))
        amount = Decimal(str(self.amount))
        return (amount * multiplier).quantize(Decimal('0.01'))

    @property
    def yearly_cost(self) -> Decimal:
        """Return the annualised cost of this subscription."""
        return (self.monthly_cost * 12).quantize(Decimal('0.01'))

    @property
    def days_until_billing(self) -> int:
        """Days remaining until the next billing date."""
        return (self.next_billing_date - date.today()).days

    @property
    def trial_days_remaining(self) -> int | None:
        """Days remaining in the trial period, or None if not a trial."""
        if self.is_trial and self.trial_end_date:
            return (self.trial_end_date - date.today()).days
        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        if self.is_trial and not self.trial_end_date:
            raise ValidationError({'trial_end_date': 'Trial end date is required when the subscription is a trial.'})

class PaymentStatus(models.TextChoices):
    EXPECTED = 'expected', 'Expected'
    CONFIRMED = 'confirmed', 'Confirmed'


class PaymentRecord(models.Model):
    """Expected renewal or confirmed payment, stored in its original currency."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, blank=True, default='')
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CONFIRMED,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['subscription', 'date'],
                condition=Q(status=PaymentStatus.EXPECTED),
                name='unique_expected_renewal_per_date',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.subscription.name} – {self.amount} on {self.date}'

    def save(self, *args, **kwargs):
        if not self.currency:
            self.currency = self.subscription.currency
        if self.status == PaymentStatus.CONFIRMED and self.confirmed_at is None:
            self.confirmed_at = timezone.now()
        elif self.status == PaymentStatus.EXPECTED:
            self.confirmed_at = None
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'currency', 'confirmed_at'}
        super().save(*args, **kwargs)
