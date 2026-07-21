import os
import unittest

from main import App
from modules.cpu_service import CpuService
from modules.hardware_service import HardwareService
from modules.smart_service import SmartService


class HardwareServiceTests(unittest.TestCase):
    def test_collect_returns_structure_without_errors(self):
        service = HardwareService()
        data = service.collect()
        self.assertIsInstance(data, dict)
        self.assertIn("cpu", data)
        self.assertIn("memory", data)
        self.assertIn("disks", data)
        self.assertIn("system", data)
        self.assertIn("sensors", data)
        self.assertIsInstance(data["sensors"], list)
        self.assertIsInstance(data["disks"], list)
        self.assertIsInstance(data["collected_at"], str)

    def test_collect_writes_debug_and_log_files(self):
        service = HardwareService()
        data = service.collect()
        self.assertTrue(os.path.exists(data["debug_file"]))
        if data.get("log_file"):
            self.assertTrue(os.path.exists(data["log_file"]))

    def test_cpu_service_prefers_aggregate_metrics_over_core_sensors(self):
        service = CpuService()
        snapshot = {
            "cpu": {"name": "CPU Test", "usage": "Não suportado pelo dispositivo."},
            "sensors": [
                {"sensor_type": "temperature", "sensor": "CPU Core #2", "value": "78.0°C"},
                {"sensor_type": "temperature", "sensor": "CPU Package", "value": "46.5°C"},
                {"sensor_type": "load", "sensor": "CPU Core #2", "value": "85.0"},
                {"sensor_type": "load", "sensor": "CPU Total", "value": "34.0"},
            ],
        }

        result = service.collect(snapshot, {"architecture": "x64"})

        self.assertEqual(result["usage"], "34.0%")
        self.assertEqual(result["temperature"], "46.5°C")

    def test_smart_service_adds_disk_metadata_fields(self):
        service = SmartService()
        result = service.collect([{"name": "Disk", "temperature": "Não suportado pelo dispositivo.", "smart_health": "Não suportado pelo dispositivo."}])
        self.assertTrue(result)
        self.assertIn("interface", result[0])
        self.assertIn("firmware", result[0])
        self.assertIn("host_writes", result[0])
        self.assertIn("host_reads", result[0])

    def test_format_hardware_detail_value_handles_lists_and_strings(self):
        self.assertEqual(App._format_hardware_detail_value(["CPU", "32.0°C"]), "CPU, 32.0°C")
        self.assertEqual(App._format_hardware_detail_value(None), "Não disponível")
        self.assertEqual(App._format_hardware_detail_value(""), "Não disponível")


if __name__ == "__main__":
    unittest.main()
