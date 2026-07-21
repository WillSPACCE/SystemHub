import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main


class HardwareAnalysisPageTest(unittest.TestCase):
    def setUp(self):
        self.app = main.App()
        self.app.withdraw()
        self.app.update_idletasks()

    def tearDown(self):
        if self.app.winfo_exists():
            self.app.destroy()

    def test_hardware_page_exposes_analysis_actions(self):
        self.assertTrue(hasattr(self.app, "hardware_update_button"))
        self.assertTrue(hasattr(self.app, "hardware_save_button"))
        self.assertEqual(self.app.hardware_update_button.cget("text"), "Atualizar lista")
        self.assertEqual(self.app.hardware_save_button.cget("text"), "Salvar lista")

    def test_save_hardware_analysis_writes_json_file(self):
        self.app.data = {
            "cpu": {"name": "Test CPU", "usage": 44},
            "memory": {"total": "16 GB", "percent": 55},
            "system": {"os_name": "Windows 11"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = self.app.save_hardware_analysis(output_dir=temp_dir)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["cpu"]["name"], "Test CPU")
            self.assertEqual(payload["system"]["os_name"], "Windows 11")


if __name__ == "__main__":
    unittest.main()
