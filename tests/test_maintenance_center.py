import os
import subprocess
from datetime import datetime

from modules.cleaner import CleanupManager
from modules.email_service import ResendEmailService
from modules.maintenance import MaintenanceCoordinator
from modules.report import ReportGenerator, format_brazilian_date, get_latest_report_path


def test_cleanup_estimate_returns_zero_for_missing_paths(tmp_path):
    manager = CleanupManager(base_dir=tmp_path)
    estimate = manager.estimate_recovery(["temp_windows", "temp_user"])

    assert estimate["total_bytes"] == 0
    assert estimate["total_human"] == "0 B"


def test_sensitive_cleanup_actions_are_unselected_by_default(tmp_path):
    manager = CleanupManager(base_dir=str(tmp_path))
    actions = {action["id"]: action for action in manager.get_default_actions()}

    assert actions["temp_windows"]["default_selected"] is True
    assert actions["temp_user"]["default_selected"] is True
    assert actions["old_windows_installations"]["default_selected"] is False
    assert actions["disk_cleanup"]["default_selected"] is False
    assert actions["registry_backup"]["default_selected"] is False
    assert actions["recycle_bin"]["default_selected"] is False


def test_sensitive_cleanup_actions_do_not_open_windows_tools(monkeypatch, tmp_path):
    manager = CleanupManager(base_dir=str(tmp_path))
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append(("popen", args, kwargs))
        return object()

    def fake_run(*args, **kwargs):
        calls.append(("run", args, kwargs))
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("modules.cleaner.subprocess.Popen", fake_popen)
    monkeypatch.setattr("modules.cleaner.subprocess.run", fake_run)

    disk_result = manager._run_disk_cleanup()
    registry_result = manager._run_registry_backup()

    assert disk_result["status"] == "OK"
    assert "aberto" not in disk_result["message"].lower()
    assert registry_result["status"] == "OK"
    assert "regedit" not in registry_result["message"].lower()
    assert all(call[0] != "popen" for call in calls)


def test_report_generator_writes_txt_report(tmp_path):
    generator = ReportGenerator(output_dir=str(tmp_path))
    report_path = generator.write_report(
        title="INFOCASE CHECKUP",
        initial_payload={"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}},
        final_payload={"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}},
        cleanup_results=[{"name": "Temp Windows", "status": "OK", "freed": "0 B"}],
        recovered_bytes=0,
        maintenance_duration="00:00:01",
        overall_status="OK",
    )

    assert os.path.exists(report_path)
    assert "INFOCASE CHECKUP" in open(report_path, encoding="utf-8").read()


def test_email_service_builds_payload_for_resend(tmp_path):
    attachment_path = tmp_path / "report.txt"
    attachment_path.write_text("teste", encoding="utf-8")
    service = ResendEmailService(api_key="test-key", from_email="sender@example.com")

    payload = service._build_payload("dest@example.com", "Assunto", "Mensagem", str(attachment_path))

    assert payload["from"] == "sender@example.com"
    assert payload["to"] == ["dest@example.com"]
    assert payload["subject"] == "Assunto"
    assert payload["text"] == "Mensagem"
    assert payload["attachments"][0]["filename"] == "report.txt"


def test_get_latest_report_path_prefers_newest_file(tmp_path):
    older_path = tmp_path / "Relatorio_2026-07-15.txt"
    newer_path = tmp_path / "Relatorio_2026-07-16.txt"
    older_path.write_text("older", encoding="utf-8")
    newer_path.write_text("newer", encoding="utf-8")

    old_time = 1710000000
    new_time = 1710003600
    os.utime(older_path, (old_time, old_time))
    os.utime(newer_path, (new_time, new_time))

    assert get_latest_report_path(str(tmp_path)) == str(newer_path)


def test_format_brazilian_date_uses_brazilian_format():
    assert format_brazilian_date(datetime(2026, 7, 16, 10, 30, 0)) == "16/07/2026"


def test_report_generator_summarizes_cleanup_without_listing_each_item(tmp_path):
    generator = ReportGenerator(output_dir=str(tmp_path))
    report_path = generator.write_report(
        title="INFOCASE CHECKUP",
        initial_payload={"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}},
        final_payload={"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}},
        cleanup_results=[{"name": "Temp Windows", "status": "OK", "freed": "10 MB"}],
        recovered_bytes=10 * 1024 * 1024,
        maintenance_duration="00:00:02",
        overall_status="OK",
    )

    content = open(report_path, encoding="utf-8").read()
    assert "Resumo da Limpeza" in content
    assert "Espaço recuperado" in content
    assert "Temp Windows" not in content


def test_run_maintenance_uses_sender_from_settings(tmp_path):
    class DummyCleaner:
        def run_cleanup(self, selected_ids=None, progress_callback=None):
            return []

        def get_default_actions(self):
            return []

    class DummyReportGenerator:
        def write_report(self, **kwargs):
            report_path = tmp_path / "report.txt"
            report_path.write_text("report", encoding="utf-8")
            return str(report_path)

    class DummyHistoryManager:
        def __init__(self):
            self.records = []

        def append(self, record):
            self.records.append(record)

    class DummyEmailService:
        def __init__(self):
            self.api_key = None
            self.from_email = "default@example.com"
            self.calls = []

        def send_report(self, recipient_email, subject, body, attachment_path):
            self.calls.append({"recipient_email": recipient_email, "subject": subject, "body": body, "attachment_path": attachment_path})

    coordinator = MaintenanceCoordinator(
        cleaner=DummyCleaner(),
        report_generator=DummyReportGenerator(),
        history_manager=DummyHistoryManager(),
        email_service=DummyEmailService(),
    )

    coordinator.run_maintenance(
        selected_ids=[],
        initial_payload={"system": {"computer_name": "PC-TEST"}},
        final_payload={"system": {"computer_name": "PC-TEST"}},
        settings={"auto_send": True, "recipient_email": "dest@example.com", "resend_api_key": "test-key", "from_email": "sender@example.com"},
    )

    assert coordinator.email_service.from_email == "sender@example.com"
    assert coordinator.email_service.calls[0]["recipient_email"] == "dest@example.com"
