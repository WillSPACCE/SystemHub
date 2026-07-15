import os
import tempfile

from modules.cleaner import CleanupManager
from modules.report import ReportGenerator


def test_cleanup_estimate_returns_zero_for_missing_paths(tmp_path):
    manager = CleanupManager(base_dir=tmp_path)
    estimate = manager.estimate_recovery(["temp_windows", "temp_user"])

    assert estimate["total_bytes"] == 0
    assert estimate["total_human"] == "0 B"


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
