"""Business-logic helpers for the subscriptions app."""

from __future__ import annotations

import csv
import unicodedata
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from django.db.models import Q, QuerySet
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.subscriptions.models import (
    BillingCycle,
    Subscription,
    SubscriptionStatus,
)

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


# ------------------------------------------------------------------
# Querying
# ------------------------------------------------------------------


def get_user_subscriptions(user: User, filters: dict | None = None) -> QuerySet[Subscription]:
    """Return subscriptions owned by *user*, optionally filtered.

    Supported filter keys:
      - search (str)   – case-insensitive name search
      - category (int)  – category PK
      - status (str)    – SubscriptionStatus value
      - sort_by (str)   – field name, prefix ``-`` for descending
    """
    qs = Subscription.objects.filter(user=user).select_related('category')

    if not filters:
        return qs

    search = filters.get('search')
    if search:
        qs = qs.filter(name__icontains=search)

    category = filters.get('category')
    if category:
        qs = qs.filter(category_id=category)

    status = filters.get('status')
    if status:
        qs = qs.filter(status=status)

    sort_by = filters.get('sort_by')
    if sort_by:
        qs = qs.order_by(sort_by)

    return qs


# ------------------------------------------------------------------
# Aggregation
# ------------------------------------------------------------------


def calculate_monthly_total(user: User) -> Decimal:
    """Return the total estimated monthly spend for active subscriptions."""
    subs = Subscription.objects.filter(user=user, status=SubscriptionStatus.ACTIVE)
    return sum((s.monthly_cost for s in subs), Decimal('0.00'))


def calculate_yearly_total(user: User) -> Decimal:
    """Return the total estimated yearly spend for active subscriptions."""
    return (calculate_monthly_total(user) * 12).quantize(Decimal('0.01'))


# ------------------------------------------------------------------
# Upcoming & Trials
# ------------------------------------------------------------------


def get_upcoming_renewals(user: User, days: int = 30) -> QuerySet[Subscription]:
    """Return active subscriptions whose next billing date is within *days*."""
    horizon = date.today() + timedelta(days=days)
    return (
        Subscription.objects.filter(
            user=user,
            status=SubscriptionStatus.ACTIVE,
            next_billing_date__lte=horizon,
            next_billing_date__gte=date.today(),
        )
        .select_related('category')
        .order_by('next_billing_date')
    )


def get_expiring_trials(user: User, days: int = 7) -> QuerySet[Subscription]:
    """Return subscriptions with trials ending within *days*."""
    horizon = date.today() + timedelta(days=days)
    return (
        Subscription.objects.filter(
            Q(is_trial=True) | Q(status='trial'),
            user=user,
            trial_end_date__lte=horizon,
            trial_end_date__gte=date.today(),
            status__in=[SubscriptionStatus.ACTIVE, 'trial'],
        )
        .select_related('category')
        .order_by('trial_end_date')
    )


# ------------------------------------------------------------------
# Billing-date advancement
# ------------------------------------------------------------------

_CYCLE_DELTA = {
    BillingCycle.WEEKLY: timedelta(weeks=1),
    BillingCycle.MONTHLY: timedelta(days=30),
    BillingCycle.QUARTERLY: timedelta(days=91),
    BillingCycle.YEARLY: timedelta(days=365),
}


def advance_billing_date(subscription: Subscription) -> date:
    """Advance *subscription.next_billing_date* by one billing cycle and save.

    Returns the new ``next_billing_date``.
    """
    delta = _CYCLE_DELTA.get(subscription.billing_cycle, timedelta(days=30))
    subscription.next_billing_date += delta
    subscription.save(update_fields=['next_billing_date'])
    return subscription.next_billing_date


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------


def export_subscriptions_csv(user: User) -> HttpResponse:
    """Return an ``HttpResponse`` containing all user subscriptions as CSV."""
    subs = Subscription.objects.filter(user=user).select_related('category').order_by('name')

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'Name', 'Category', 'Amount', 'Currency', 'Billing Cycle',
        'Start Date', 'Next Billing Date', 'Status', 'Is Trial',
        'Trial End Date', 'Payment Method', 'Website', 'Notes',
    ])

    for sub in subs:
        writer.writerow([
            sub.name,
            sub.category.name if sub.category else '',
            str(sub.amount),
            sub.currency,
            sub.get_billing_cycle_display(),
            sub.start_date.isoformat(),
            sub.next_billing_date.isoformat(),
            sub.get_status_display(),
            'Yes' if sub.is_trial else 'No',
            sub.trial_end_date.isoformat() if sub.trial_end_date else '',
            sub.payment_method,
            sub.website_url,
            sub.notes,
        ])

    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="subscriptions.csv"'
    return response


def export_subscriptions_pdf(user: User) -> HttpResponse:
    """Build a printable PDF report containing only the user's subscriptions."""
    subscriptions = list(
        Subscription.objects.filter(user=user).select_related('category').order_by('name')
    )
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title='SubSentinel Subscription Report',
        author='SubSentinel',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle', parent=styles['Title'], fontName='Helvetica-Bold',
        fontSize=20, leading=24, textColor=colors.HexColor('#312E81'), alignment=TA_LEFT,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='ReportMeta', parent=styles['Normal'], fontSize=9, leading=12,
        textColor=colors.HexColor('#64748B'), spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name='TableCell', parent=styles['BodyText'], fontName='Helvetica',
        fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'),
    ))
    styles.add(ParagraphStyle(
        name='TableHeader', parent=styles['BodyText'], fontName='Helvetica-Bold',
        fontSize=8, leading=10, textColor=colors.white,
    ))

    def cell_text(value) -> Paragraph:
        normalized = unicodedata.normalize('NFKD', str(value))
        printable = normalized.encode('cp1252', errors='replace').decode('cp1252')
        return Paragraph(escape(printable), styles['TableCell'])

    elements = [
        Paragraph('SubSentinel Subscription Report', styles['ReportTitle']),
        Paragraph(
            f'Generated {timezone.localdate():%B %d, %Y} &nbsp; | &nbsp; '
            f'{len(subscriptions)} subscription{"s" if len(subscriptions) != 1 else ""}',
            styles['ReportMeta'],
        ),
    ]

    headings = ['Service', 'Category', 'Amount', 'Billing', 'Status', 'Next bill', 'Trial ends']
    rows = [[Paragraph(heading, styles['TableHeader']) for heading in headings]]
    for subscription in subscriptions:
        values = [
            subscription.name,
            subscription.category.name if subscription.category else '—',
            f'{subscription.amount:,.2f} {subscription.currency}',
            subscription.get_billing_cycle_display(),
            subscription.get_status_display(),
            subscription.next_billing_date.strftime('%b %d, %Y'),
            subscription.trial_end_date.strftime('%b %d, %Y') if subscription.trial_end_date else '—',
        ]
        rows.append([cell_text(value) for value in values])

    if len(rows) == 1:
        elements.append(Paragraph('No subscriptions have been added yet.', styles['BodyText']))
    else:
        table = Table(
            rows,
            colWidths=[width * inch for width in [1.65, 1.25, 1.05, 1.0, 1.0, 1.15, 1.1]],
            repeatRows=1,
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#4338CA')),
            ('LINEBELOW', (0, 1), (-1, -1), 0.35, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        elements.extend([table, Spacer(1, 10)])

    def draw_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748B'))
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.3 * inch, f'Page {doc.page}')
        canvas.restoreState()

    document.build(elements, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="subscriptions.pdf"'
    return response
