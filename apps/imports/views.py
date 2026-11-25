from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.imports.forms import CSVUploadForm
from apps.imports.models import CandidateStatus, DetectedCandidate, StatementUpload, UploadStatus
from apps.imports.services import detect_recurring, parse_csv
from apps.subscriptions.models import Subscription, SubscriptionStatus


@login_required
def upload_csv(request):
    """Accept a CSV file upload and run subscription detection."""
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']

            upload = StatementUpload.objects.create(
                user=request.user,
                file_name=uploaded_file.name,
                status=UploadStatus.PROCESSING,
            )

            try:
                df = parse_csv(uploaded_file)
                upload.row_count = len(df)
                candidates = detect_recurring(df)

                for c in candidates:
                    DetectedCandidate.objects.create(
                        upload=upload,
                        merchant_name=c['merchant_name'],
                        normalized_name=c['normalized_name'],
                        amount=c['amount'],
                        interval=c['interval'],
                        confidence=c['confidence'],
                        next_expected_date=c.get('next_expected_date'),
                        transaction_count=c['transaction_count'],
                    )

                upload.status = UploadStatus.COMPLETED
                upload.save()
                messages.success(
                    request,
                    f'Processed {upload.row_count} rows — found {len(candidates)} potential subscriptions.',
                )
                return redirect('imports:review', upload_id=upload.pk)

            except ValueError as exc:
                upload.status = UploadStatus.FAILED
                upload.error_message = str(exc)
                upload.save()
                messages.error(request, f'Import failed: {exc}')

    else:
        form = CSVUploadForm()

    uploads = StatementUpload.objects.filter(user=request.user)[:10]
    return render(request, 'imports/upload.html', {'form': form, 'uploads': uploads})


@login_required
def review_candidates(request, upload_id: int):
    """Display detected subscription candidates for review."""
    upload = get_object_or_404(StatementUpload, pk=upload_id, user=request.user)
    candidates = upload.candidates.all()
    return render(request, 'imports/review.html', {
        'upload': upload,
        'candidates': candidates,
    })


@login_required
@require_POST
def confirm_candidate(request, candidate_id: int):
    """Confirm a detected candidate and create a Subscription (HTMX)."""
    candidate = get_object_or_404(
        DetectedCandidate,
        pk=candidate_id,
        upload__user=request.user,
    )

    if candidate.status == CandidateStatus.PENDING:
        subscription = Subscription.objects.create(
            user=request.user,
            name=candidate.merchant_name,
            amount=candidate.amount,
            currency=request.user.settings.default_currency,
            billing_cycle=candidate.interval,
            start_date=date.today(),
            next_billing_date=candidate.next_expected_date or date.today(),
            status=SubscriptionStatus.ACTIVE,
        )
        candidate.status = CandidateStatus.CONFIRMED
        candidate.subscription = subscription
        candidate.save(update_fields=['status', 'subscription'])

    messages.success(request, f'"{candidate.merchant_name}" added as a subscription.')

    if request.headers.get('HX-Request'):
        return render(request, 'imports/partials/candidate_row.html', {'candidate': candidate})
    return redirect('imports:review', upload_id=candidate.upload_id)


@login_required
@require_POST
def dismiss_candidate(request, candidate_id: int):
    """Dismiss a detected candidate (HTMX)."""
    candidate = get_object_or_404(
        DetectedCandidate,
        pk=candidate_id,
        upload__user=request.user,
    )

    if candidate.status == CandidateStatus.PENDING:
        candidate.status = CandidateStatus.DISMISSED
        candidate.save(update_fields=['status'])

    messages.info(request, f'"{candidate.merchant_name}" dismissed.')

    if request.headers.get('HX-Request'):
        return render(request, 'imports/partials/candidate_row.html', {'candidate': candidate})
    return redirect('imports:review', upload_id=candidate.upload_id)


@login_required
@require_POST
def bulk_confirm(request, upload_id: int):
    """Confirm all pending candidates in a single action."""
    upload = get_object_or_404(StatementUpload, pk=upload_id, user=request.user)
    pending = upload.candidates.filter(status=CandidateStatus.PENDING)
    count = 0

    for candidate in pending:
        subscription = Subscription.objects.create(
            user=request.user,
            name=candidate.merchant_name,
            amount=candidate.amount,
            currency=request.user.settings.default_currency,
            billing_cycle=candidate.interval,
            start_date=date.today(),
            next_billing_date=candidate.next_expected_date or date.today(),
            status=SubscriptionStatus.ACTIVE,
        )
        candidate.status = CandidateStatus.CONFIRMED
        candidate.subscription = subscription
        candidate.save()
        count += 1

    messages.success(request, f'Confirmed {count} subscriptions.')
    return redirect('imports:review', upload_id=upload_id)


@login_required
@require_POST
def bulk_dismiss(request, upload_id: int):
    """Dismiss all pending candidates in an upload."""
    upload = get_object_or_404(StatementUpload, pk=upload_id, user=request.user)
    count = upload.candidates.filter(status=CandidateStatus.PENDING).update(
        status=CandidateStatus.DISMISSED,
    )
    messages.info(request, f'Dismissed {count} candidates.')
    return redirect('imports:review', upload_id=upload_id)


@login_required
def sample_csv(request):
    """Download the sample bank-statement CSV file."""
    from pathlib import Path

    from django.conf import settings
    from django.http import HttpResponse

    sample_path = Path(settings.BASE_DIR) / 'sample_data' / 'sample_statement.csv'
    content = sample_path.read_text(encoding='utf-8') if sample_path.exists() else 'date,description,amount\n'
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_statement.csv"'
    return response
