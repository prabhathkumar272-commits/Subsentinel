"""Check whether the database and cache dependencies are ready."""

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = 'Fail unless the configured database and cache can serve requests.'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception as exc:
            raise CommandError('Database readiness check failed.') from exc

        executor = MigrationExecutor(connection)
        pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if pending:
            raise CommandError('Database migrations are pending.')

        key = 'subsentinel:container-healthcheck'
        try:
            cache.set(key, 'ok', timeout=5)
            if cache.get(key) != 'ok':
                raise RuntimeError('Cache health probe did not round-trip.')
        except Exception as exc:
            raise CommandError('Cache readiness check failed.') from exc

        self.stdout.write(self.style.SUCCESS('Database and cache are ready.'))
