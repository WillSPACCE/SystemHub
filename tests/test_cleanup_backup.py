import os
import shutil
import tempfile
from datetime import datetime, timedelta

from modules.cleaner import CleanupManager


def test_cleanup_creates_backup_and_retains_for_30_days(tmp_path):
    target_dir = tmp_path / "temp_target"
    target_dir.mkdir()
    file_path = target_dir / "arquivo.tmp"
    file_path.write_text("conteudo", encoding="utf-8")

    manager = CleanupManager(base_dir=str(tmp_path))
    action = {
        "id": "temp_test",
        "name": "Temp Teste",
        "label": "Limpar pasta de teste",
        "paths": [str(target_dir)],
    }

    result = manager._run_action(action)

    assert result["status"] == "OK"
    assert not file_path.exists()

    backup_root = tmp_path / "temp_target_backup"
    assert backup_root.exists()
    assert (backup_root / "arquivo.tmp").exists()

    old_backup = backup_root / "velho.tmp"
    old_backup.write_text("antigo", encoding="utf-8")
    old_backup_time = datetime.now() - timedelta(days=31)
    os.utime(old_backup, (old_backup_time.timestamp(), old_backup_time.timestamp()))

    manager._prune_old_backups(backup_root)
    assert not old_backup.exists()

    shutil.rmtree(tmp_path, ignore_errors=True)
