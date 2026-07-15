import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.system_service import SystemService


def test_collect_exposes_windows_version_and_update_status(monkeypatch):
    service = SystemService()

    monkeypatch.setattr(service, "_get_windows_version", lambda: "Windows 11 (26100)")
    monkeypatch.setattr(service, "_get_windows_update_status", lambda: "Atualizações em dia")

    data = service.collect()

    assert data["version"] == "Windows 11 (26100)"
    assert data["update_status"] == "Atualizações em dia"
