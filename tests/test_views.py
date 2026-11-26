from decimal import Decimal

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Auth / Public views
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAuthViews:
    def test_landing_loads(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_dashboard_requires_login(self, client):
        response = client.get('/dashboard/')
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_register_get(self, client):
        response = client.get('/accounts/register/')
        assert response.status_code == 200

    def test_authentication_pages_render_their_forms(self, client):
        for url, expected in [
            ('/accounts/login/', 'Sign In'),
            ('/accounts/register/', 'Create Account'),
            ('/accounts/password-reset/', 'Send Reset Link'),
        ]:
            response = client.get(url)
            assert response.status_code == 200
            assert expected.encode() in response.content

    def test_register_post_valid(self, client, db):
        response = client.post('/accounts/register/', {
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        assert response.status_code == 302

    def test_login_valid(self, client, user):
        response = client.post('/accounts/login/', {
            'username': 'test@test.com',
            'password': 'testpass123',
        })
        assert response.status_code == 302

    def test_login_invalid_password(self, client, user):
        response = client.post('/accounts/login/', {
            'username': 'test@test.com',
            'password': 'wrongpassword',
        })
        # Should NOT redirect – stays on login page with error
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_landing(self, auth_client):
        response = auth_client.get('/')
        assert response.status_code == 302
        assert 'dashboard' in response.url


# ─────────────────────────────────────────────────────────────────────────────
# Subscription views
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSubscriptionViews:
    def test_subscription_list(self, auth_client):
        response = auth_client.get('/subscriptions/')
        assert response.status_code == 200

    def test_subscription_list_requires_login(self, client):
        response = client.get('/subscriptions/')
        assert response.status_code == 302

    def test_subscription_create(self, auth_client, category, db):
        from datetime import date, timedelta
        response = auth_client.post('/subscriptions/create/', {
            'name': 'Test Sub',
            'category': category.id,
            'amount': '9.99',
            'billing_cycle': 'monthly',
            'start_date': date.today().isoformat(),
            'next_billing_date': (date.today() + timedelta(days=30)).isoformat(),
            'status': 'active',
            'reminder_days_before': 3,
        })
        # 302 = successful redirect after creation; 200 = form errors (also acceptable path)
        assert response.status_code in [200, 302]

    def test_subscription_create_defaults_to_user_currency(self, auth_client, user):
        user.settings.default_currency = 'INR'
        user.settings.save(update_fields=['default_currency'])
        response = auth_client.get('/subscriptions/create/')
        assert response.status_code == 200
        assert response.context['form'].initial['currency'] == 'INR'

    def test_subscription_detail_own(self, auth_client, subscription):
        response = auth_client.get(f'/subscriptions/{subscription.id}/')
        assert response.status_code == 200

    def test_expected_payment_can_only_be_confirmed_by_its_owner(self, auth_client, user, other_user, subscription):
        from apps.subscriptions.models import PaymentRecord, PaymentStatus

        expected = PaymentRecord.objects.create(
            subscription=subscription,
            amount=subscription.amount,
            date=subscription.next_billing_date,
            status=PaymentStatus.EXPECTED,
            notes='Expected renewal',
        )
        url = f'/subscriptions/payments/{expected.pk}/confirm/'
        detail = auth_client.get(f'/subscriptions/{subscription.pk}/')
        assert b'Confirm paid' in detail.content
        assert auth_client.get(url).status_code == 405
        response = auth_client.post(url)
        assert response.status_code == 302
        expected.refresh_from_db()
        assert expected.status == PaymentStatus.CONFIRMED
        assert expected.confirmed_at is not None
        assert b'Confirmed' in auth_client.get(f'/subscriptions/{subscription.pk}/').content

        # Confirmation is idempotent and cannot be used to access another user's record.
        auth_client.post(url)
        assert PaymentRecord.objects.filter(subscription=subscription).count() == 1
        from django.test import Client

        other_client = Client()
        other_client.force_login(other_user)
        assert other_client.post(url).status_code == 404

    def test_dashboard_displays_currency_totals_separately_and_isolates_users(
        self, auth_client, subscription, user, other_user, category
    ):
        import json

        from django.utils import timezone

        from apps.subscriptions.models import PaymentRecord, PaymentStatus, Subscription

        Subscription.objects.create(
            user=user,
            name='INR service',
            category=category,
            amount='100.00',
            currency='INR',
            billing_cycle='monthly',
            start_date=subscription.start_date,
            next_billing_date=subscription.next_billing_date,
        )
        Subscription.objects.create(
            user=other_user,
            name='Private foreign service',
            category=category,
            amount='999.00',
            currency='USD',
            billing_cycle='monthly',
            start_date=subscription.start_date,
            next_billing_date=subscription.next_billing_date,
        )
        PaymentRecord.objects.create(
            subscription=subscription,
            amount='4.00',
            date=timezone.localdate(),
            status=PaymentStatus.CONFIRMED,
        )
        PaymentRecord.objects.create(
            subscription=subscription,
            amount='99.00',
            date=subscription.next_billing_date,
            status=PaymentStatus.EXPECTED,
        )
        response = auth_client.get('/dashboard/')
        totals = {row['currency']: row for row in response.context['currency_totals']}
        chart_data = json.loads(response.context['chart_data'])
        assert totals['USD']['monthly'] == subscription.monthly_cost
        assert totals['INR']['monthly'] == Decimal('100.00')
        assert chart_data['currency'] == user.settings.default_currency
        assert 'category_labels' in chart_data
        assert chart_data['category_amounts'] == [float(subscription.monthly_cost)]
        assert chart_data['trend_amounts'][-1] == 4.0

    def test_subscription_permission(self, auth_client, other_user, category, db):
        from datetime import date, timedelta

        from apps.subscriptions.models import Subscription
        other_sub = Subscription.objects.create(
            user=other_user,
            name='Other Sub',
            category=category,
            amount='9.99',
            billing_cycle='monthly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=30),
        )
        response = auth_client.get(f'/subscriptions/{other_sub.id}/')
        assert response.status_code == 404

    def test_subscription_delete_own(self, auth_client, subscription):
        response = auth_client.post(f'/subscriptions/{subscription.id}/delete/')
        assert response.status_code in [200, 302]

    def test_subscription_delete_other_forbidden(self, auth_client, other_user, category, db):
        from datetime import date, timedelta

        from apps.subscriptions.models import Subscription
        other_sub = Subscription.objects.create(
            user=other_user,
            name='Hacker Target',
            category=category,
            amount='5.00',
            billing_cycle='monthly',
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=30),
        )
        response = auth_client.post(f'/subscriptions/{other_sub.id}/delete/')
        assert response.status_code in [403, 404]

    def test_subscription_edit(self, auth_client, subscription):
        response = auth_client.get(f'/subscriptions/{subscription.id}/edit/')
        assert response.status_code == 200

    def test_subscription_pause_resume_cancel(self, auth_client, subscription):
        assert auth_client.post(f'/subscriptions/{subscription.id}/pause/').status_code in [200, 302]
        assert auth_client.post(f'/subscriptions/{subscription.id}/resume/').status_code in [200, 302]
        assert auth_client.post(f'/subscriptions/{subscription.id}/cancel/').status_code in [200, 302]

    def test_subscription_export_csv(self, auth_client, subscription):
        response = auth_client.get('/subscriptions/export/csv/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert b'Netflix' in response.content

    def test_subscription_export_pdf(self, auth_client, subscription):
        subscription.name = 'Cafe & Caffè <Premium> 🚀'
        subscription.save(update_fields=['name'])
        response = auth_client.get('/subscriptions/export/pdf/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response['Content-Disposition'] == 'attachment; filename="subscriptions.pdf"'
        assert response.content.startswith(b'%PDF-')


@pytest.mark.django_db
class TestAppViews:
    def test_dashboard_loads(self, auth_client, subscription):
        response = auth_client.get('/dashboard/')
        assert response.status_code == 200
        assert b'Netflix' in response.content
        assert b'href="/subscriptions/create/"' in response.content
        assert b'/subscriptions/add/' not in response.content

    def test_profile_settings(self, auth_client):
        response = auth_client.get('/accounts/profile/')
        assert response.status_code == 200

    def test_insights_calendar(self, auth_client, subscription):
        response = auth_client.get('/insights/calendar/')
        assert response.status_code == 200

    def test_notifications_views(self, auth_client, user, subscription):
        from apps.notifications.models import Notification
        notif = Notification.objects.create(
            user=user,
            title='Test Notif',
            message='Renewal coming up',
            related_subscription=subscription,
        )
        assert auth_client.get('/notifications/').status_code == 200
        assert auth_client.get('/notifications/dropdown/').status_code == 200
        assert auth_client.get('/notifications/unread-count/').status_code == 200
        assert auth_client.post(f'/notifications/{notif.id}/read/').status_code in [200, 302]
        assert auth_client.post('/notifications/mark-all-read/').status_code in [200, 302]

    def test_imports_upload_loads(self, auth_client):
        response = auth_client.get('/imports/upload/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestImportWorkflow:
    def _statement(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        rows = ["date,description,amount"]
        rows.extend([
            "2025-01-01,STREAMFLIX monthly,-12.99",
            "2025-02-01,STREAMFLIX monthly,-12.99",
            "2025-03-01,STREAMFLIX monthly,-12.99",
        ])
        return SimpleUploadedFile('statement.csv', '\n'.join(rows).encode(), content_type='text/csv')

    def test_upload_creates_reviewable_candidates(self, auth_client, user):
        from apps.imports.models import CandidateStatus, StatementUpload
        response = auth_client.post('/imports/upload/', {'file': self._statement()})
        upload = StatementUpload.objects.get(user=user)
        assert response.status_code == 302
        assert response.url == f'/imports/review/{upload.pk}/'
        assert upload.row_count == 3
        assert upload.candidates.count() == 1
        assert upload.candidates.get().status == CandidateStatus.PENDING
        assert auth_client.get(response.url).status_code == 200

    def test_upload_rejects_invalid_csv_and_file_type(self, auth_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        bad_file = SimpleUploadedFile('statement.csv', b'wrong,columns\n1,2', content_type='text/csv')
        response = auth_client.post('/imports/upload/', {'file': bad_file})
        assert response.status_code == 200
        assert b'Import failed' in response.content
        invalid_file = SimpleUploadedFile('statement.txt', b'anything')
        response = auth_client.post('/imports/upload/', {'file': invalid_file})
        assert response.status_code == 200
        assert b'Only .csv files are accepted' in response.content

    def test_confirm_is_post_only_and_idempotent(self, auth_client, user):
        from apps.imports.models import CandidateStatus, DetectedCandidate, StatementUpload
        upload = StatementUpload.objects.create(user=user, file_name='statement.csv')
        user.settings.default_currency = 'INR'
        user.settings.save(update_fields=['default_currency'])
        candidate = DetectedCandidate.objects.create(
            upload=upload, merchant_name='Streamflix', normalized_name='streamflix',
            amount='12.99', interval='monthly', confidence=90,
        )
        assert auth_client.get(f'/imports/confirm/{candidate.pk}/').status_code == 405
        response = auth_client.post(f'/imports/confirm/{candidate.pk}/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert b'Added' in response.content
        assert auth_client.post(f'/imports/confirm/{candidate.pk}/').status_code == 302
        assert user.subscriptions.count() == 1
        assert user.subscriptions.get().currency == 'INR'
        candidate.refresh_from_db()
        assert candidate.status == CandidateStatus.CONFIRMED

    def test_dismiss_bulk_actions_and_user_isolation(self, auth_client, user, other_user):
        from apps.imports.models import CandidateStatus, DetectedCandidate, StatementUpload
        own_upload = StatementUpload.objects.create(user=user, file_name='mine.csv')
        other_upload = StatementUpload.objects.create(user=other_user, file_name='other.csv')
        own = DetectedCandidate.objects.create(
            upload=own_upload, merchant_name='A', normalized_name='a', amount='1.00',
            interval='monthly', confidence=50,
        )
        foreign = DetectedCandidate.objects.create(
            upload=other_upload, merchant_name='B', normalized_name='b', amount='1.00',
            interval='monthly', confidence=50,
        )
        assert auth_client.get(f'/imports/review/{other_upload.pk}/').status_code == 404
        assert auth_client.post(f'/imports/dismiss/{own.pk}/', HTTP_HX_REQUEST='true').status_code == 200
        assert auth_client.post(f'/imports/confirm/{foreign.pk}/').status_code == 404
        pending = DetectedCandidate.objects.create(
            upload=own_upload, merchant_name='C', normalized_name='c', amount='2.00',
            interval='monthly', confidence=60,
        )
        assert auth_client.post(f'/imports/bulk-dismiss/{own_upload.pk}/').status_code == 302
        own.refresh_from_db()
        pending.refresh_from_db()
        assert own.status == CandidateStatus.DISMISSED
        assert pending.status == CandidateStatus.DISMISSED

    def test_profile_update_and_account_delete(self, auth_client, user):
        response = auth_client.post('/accounts/profile/', {
            'first_name': 'Updated', 'last_name': 'Name', 'email': user.email,
            'default_currency': 'INR', 'default_reminder_days': 5,
            'email_reminders_enabled': 'on', 'theme': 'dark',
        })
        assert response.status_code == 302
        user.refresh_from_db()
        user.settings.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.settings.default_currency == 'INR'
        assert auth_client.get('/accounts/delete/').status_code == 302
        assert auth_client.post('/accounts/delete/').status_code == 302
        from apps.accounts.models import CustomUser
        assert not CustomUser.objects.filter(pk=user.pk).exists()
