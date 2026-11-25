from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seeds default subscription categories'

    def handle(self, *args, **options):
        from apps.subscriptions.models import Category

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
            {'name': 'Finance',          'color': '#F9A825', 'icon': '💰'},
            {'name': 'VPN & Security',   'color': '#D32F2F', 'icon': '🔒'},
            {'name': 'Business',         'color': '#0288D1', 'icon': '🏢'},
            {'name': 'AI & Tools',       'color': '#7B1FA2', 'icon': '🤖'},
            {'name': 'Food & Delivery',  'color': '#EF6C00', 'icon': '🍔'},
            {'name': 'Other',            'color': '#78909C', 'icon': '📦'},
        ]

        created = 0
        skipped = 0
        for cd in categories_data:
            obj, was_created = Category.objects.get_or_create(
                name=cd['name'],
                defaults={
                    'color': cd['color'],
                    'icon': cd['icon'],
                    'is_default': True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✔  Created category: {cd["name"]}'))
            else:
                skipped += 1
                self.stdout.write(self.style.WARNING(f'  –  Already exists:  {cd["name"]}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {created} categories, skipped {skipped} existing.'
        ))
