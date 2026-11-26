"""Create or restore a PostgreSQL archive through the Compose database service."""

from __future__ import annotations

import argparse
import subprocess
from datetime import UTC, datetime
from pathlib import Path

COMPOSE = ['docker', 'compose', 'exec', '-T', 'db']


def backup(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = COMPOSE + [
        'sh',
        '-c',
        'pg_dump --format=custom --no-owner --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"',
    ]
    try:
        with destination.open('wb') as archive:
            subprocess.run(command, stdout=archive, check=True)  # noqa: S603
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    print(f'Backup written to {destination}')


def restore(source: Path, confirmed: bool) -> None:
    if not confirmed:
        raise SystemExit('Restore is destructive. Re-run with --confirm after reviewing the target database.')
    if not source.is_file():
        raise SystemExit(f'Backup archive not found: {source}')
    command = COMPOSE + [
        'sh',
        '-c',
        'pg_restore --clean --if-exists --no-owner --single-transaction '
        '--username="$POSTGRES_USER" --dbname="$POSTGRES_DB"',
    ]
    with source.open('rb') as archive:
        subprocess.run(command, stdin=archive, check=True)  # noqa: S603
    print('Database restore completed.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='action', required=True)
    backup_parser = subparsers.add_parser('backup', help='write a timestamped PostgreSQL archive')
    backup_parser.add_argument(
        '--file',
        type=Path,
        default=Path('backups') / f"subsentinel-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.dump",
    )
    restore_parser = subparsers.add_parser('restore', help='restore an archive (overwrites current data)')
    restore_parser.add_argument('--file', type=Path, required=True)
    restore_parser.add_argument('--confirm', action='store_true', help='confirm the destructive restore')
    args = parser.parse_args()
    if args.action == 'backup':
        backup(args.file)
    else:
        restore(args.file, args.confirm)


if __name__ == '__main__':
    main()
