from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

import pytest


def test_restore_requires_explicit_confirmation():
    from ops.database_backup import restore

    with pytest.raises(SystemExit, match='Restore is destructive'):
        restore(Path('missing.dump'), confirmed=False)


def test_restore_refuses_missing_archive(tmp_path):
    from ops.database_backup import restore

    with pytest.raises(SystemExit, match='Backup archive not found'):
        restore(tmp_path / 'missing.dump', confirmed=True)


def test_failed_backup_removes_incomplete_archive(tmp_path):
    from ops.database_backup import backup

    destination = tmp_path / 'partial.dump'
    with patch('ops.database_backup.subprocess.run', side_effect=CalledProcessError(1, ['docker'])):
        with pytest.raises(CalledProcessError):
            backup(destination)
    assert not destination.exists()
