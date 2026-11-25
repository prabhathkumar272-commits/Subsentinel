from django.conf import settings
from django.db import models

from apps.subscriptions.models import Subscription


class UploadStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class CandidateStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    DISMISSED = 'dismissed', 'Dismissed'


class StatementUpload(models.Model):
    """Record of a CSV file uploaded for subscription detection."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='statement_uploads',
    )
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=12,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
    )
    row_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self) -> str:
        return f'{self.file_name} ({self.get_status_display()})'


class DetectedCandidate(models.Model):
    """A potential recurring charge detected from a bank statement."""

    INTERVAL_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    upload = models.ForeignKey(
        StatementUpload,
        on_delete=models.CASCADE,
        related_name='candidates',
    )
    merchant_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    confidence = models.PositiveIntegerField(
        help_text='Confidence score 0–100',
    )
    next_expected_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=CandidateStatus.choices,
        default=CandidateStatus.PENDING,
    )
    transaction_count = models.PositiveIntegerField(default=0)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detected_candidates',
    )

    class Meta:
        ordering = ['-confidence']

    def __str__(self) -> str:
        return f'{self.merchant_name} – {self.amount} ({self.interval})'

    @property
    def confirmed(self) -> bool:
        return self.status == CandidateStatus.CONFIRMED

    @property
    def dismissed(self) -> bool:
        return self.status == CandidateStatus.DISMISSED

    @property
    def confidence_score(self) -> int:
        """Compatibility name used by the candidate review template."""
        return self.confidence

