import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seeds demo data: a demo user with subscriptions and payment history'

    def handle(self, *args, **options):
        from apps.accounts.models import CustomUser
        from apps.notifications.models import Notification
        from apps.subscriptions.models import Category, PaymentRecord, Subscription

        # ── Demo user ──────────────────────────────────────────────────────────
        demo_email = 'demo@subsentinel.com'
        if CustomUser.objects.filter(email=demo_email).exists():
            self.stdout.write(self.style.WARNING(
                'Demo user already exists – skipping seed. '
                'Delete the user first to re-seed.'
            ))
            return

        demo_user = CustomUser.objects.create_user(
            email=demo_email,
            password='demo1234!',
            first_name='Alex',
            last_name='Demo',
        )
        self.stdout.write(self.style.SUCCESS(f'✔  Created demo user: {demo_email}'))

        # ── Categories ─────────────────────────────────────────────────────────
        categories_data = [
            {'name': 'Streaming',        'color': '#E50914', 'icon': '🎬'},
            {'name': 'Music',            'color': '#1DB954', 'icon': '🎵'},
            {'name': 'Cloud & Storage',  'color': '#4285F4', 'icon': '☁️'},
            {'name': 'Gaming',           'color': '#9146FF', 'icon': '🎮'},
            {'name': 'Productivity',     'color': '#FF6F00', 'icon': '💼'},
            {'name': 'News & Media',     'color': '#1A1A2E', 'icon': '📰'},
            {'name': 'Health & Fitness', 'color': '#00C853', 'icon': '💪'},
            {'name': 'Education',        'color': '#0077B5', 'icon': '📚'},
            {'name': 'Software & Dev',   'color': '#6E40C9', 'icon': '💻'},
            {'name': 'Other',            'color': '#78909C', 'icon': '📦'},
        ]

        cat_map = {}
        for cd in categories_data:
            obj, _ = Category.objects.get_or_create(
                name=cd['name'],
                defaults={'color': cd['color'], 'icon': cd['icon'], 'is_default': True},
            )
            cat_map[cd['name']] = obj
        self.stdout.write(self.style.SUCCESS(f'✔  Created {len(cat_map)} categories'))

        # ── Subscription definitions ────────────────────────────────────────────
        today = date.today()

        def _next(days_offset):
            return today + timedelta(days=days_offset)

        subs_data = [
            # name, category, amount, cycle, status, next_offset, trial_end
            ('Netflix',          'Streaming',        '15.99',  'monthly',  'active',    3,  None),
            ('Spotify',          'Music',            '9.99',   'monthly',  'active',    7,  None),
            ('AWS',              'Cloud & Storage',  '47.00',  'monthly',  'active',   12,  None),
            ('GitHub Pro',       'Software & Dev',   '4.00',   'monthly',  'active',   15,  None),
            ('Adobe CC',         'Productivity',     '54.99',  'monthly',  'paused',   20,  None),
            ('ChatGPT Plus',     'Software & Dev',   '20.00',  'monthly',  'active',   22,  None),
            ('YouTube Premium',  'Streaming',        '13.99',  'monthly',  'active',   25,  None),
            ('Notion',           'Productivity',     '8.00',   'monthly',  'active',   28,  None),
            ('Figma',            'Software & Dev',   '12.00',  'monthly',  'active',    5,  _next(5)),
            ('Planet Fitness',   'Health & Fitness', '24.99',  'monthly',  'active',    8,  None),
            ('NYT Digital',      'News & Media',     '17.00',  'monthly',  'active',   10,  _next(10)),
            ('iCloud+',          'Cloud & Storage',  '2.99',   'monthly',  'active',   18,  None),
            ('Microsoft 365',    'Productivity',     '99.99',  'yearly',   'active',  180,  None),
            ('Slack Pro',        'Productivity',     '7.25',   'monthly',  'paused',   30,  None),
            ('Dropbox Plus',     'Cloud & Storage',  '9.99',   'monthly',  'cancelled', 0,  None),
        ]

        created_subs = []
        for (name, cat_name, amount, cycle, status, next_offset, trial_end) in subs_data:
            start = today - timedelta(days=365)
            next_billing = _next(next_offset) if status != 'cancelled' else today - timedelta(days=1)
            sub = Subscription.objects.create(
                user=demo_user,
                name=name,
                category=cat_map.get(cat_name),
                amount=Decimal(amount),
                billing_cycle=cycle,
                status=status,
                start_date=start,
                next_billing_date=next_billing,
                is_trial=trial_end is not None,
                trial_end_date=trial_end,
                reminder_days_before=3,
            )
            created_subs.append((sub, Decimal(amount), cycle))
        self.stdout.write(self.style.SUCCESS(f'✔  Created {len(created_subs)} subscriptions'))

        # ── Payment history (12 months back for active/paused subs) ─────────────
        payment_count = 0
        for sub, amount, cycle in created_subs:
            if sub.status == 'cancelled':
                continue
            months = 12 if cycle == 'monthly' else 1
            for m in range(months, 0, -1):
                pay_date = today - timedelta(days=30 * m)
                # slight jitter ±2 days
                pay_date += timedelta(days=random.randint(-2, 2))
                PaymentRecord.objects.create(
                    subscription=sub,
                    amount=amount,
                    date=pay_date,
                    notes='Automatic recurring billing',
                )
                payment_count += 1
        self.stdout.write(self.style.SUCCESS(f'✔  Created {payment_count} payment records'))

        # ── Sample notifications ────────────────────────────────────────────────
        notifications = [
            {
                'title': 'Figma trial ending soon',
                'message': 'Your Figma trial ends in 5 days. Upgrade or cancel to avoid charges.',
                'notification_type': 'trial_expiry',
                'is_read': False,
            },
            {
                'title': 'Netflix renewal tomorrow',
                'message': 'Netflix ($15.99) renews tomorrow.',
                'notification_type': 'renewal_reminder',
                'is_read': False,
            },
            {
                'title': 'NYT trial ending in 10 days',
                'message': 'Your NYT Digital trial ends in 10 days.',
                'notification_type': 'trial_expiry',
                'is_read': True,
            },
        ]
        for nd in notifications:
            Notification.objects.create(user=demo_user, **nd)
        self.stdout.write(self.style.SUCCESS(f'✔  Created {len(notifications)} notifications'))

        self.stdout.write(self.style.SUCCESS(
            '\n🎉  Demo seed complete!\n'
            f'    Email   : {demo_email}\n'
            f'    Password: demo1234!\n'
        ))
