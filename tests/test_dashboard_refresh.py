import unittest

import main


class DashboardRefreshTest(unittest.TestCase):
    def setUp(self):
        self.app = main.App()
        self.app.withdraw()
        self.app.update_idletasks()

    def tearDown(self):
        if self.app.winfo_exists():
            self.app.destroy()

    def test_refresh_updates_dashboard_without_recreating_widgets(self):
        first_payload = {
            "cpu": {"name": "Intel Core i5", "usage": 45, "temperature": 58, "clock_current": 3200, "threads": 8, "physical_cores": 4},
            "memory": {"total": "16 GB", "used": "7 GB", "free": "9 GB", "percent": 45},
            "disks": [{"model": "SSD 970 EVO", "name": "SSD", "used": "400 GB", "total": "1000 GB", "free": "600 GB", "temperature": 42, "smart_health": 98}],
            "system": {"os_name": "Windows 11", "version": "24H2", "uptime": 3600, "architecture": "64-bit", "computer_name": "DESKTOP"},
            "collected_at": "10:00",
        }
        second_payload = {
            "cpu": {"name": "Intel Core i5", "usage": 78, "temperature": 72, "clock_current": 3400, "threads": 8, "physical_cores": 4},
            "memory": {"total": "16 GB", "used": "12 GB", "free": "4 GB", "percent": 75},
            "disks": [{"model": "SSD 970 EVO", "name": "SSD", "used": "700 GB", "total": "1000 GB", "free": "300 GB", "temperature": 49, "smart_health": 92}],
            "system": {"os_name": "Windows 11", "version": "24H2", "uptime": 7200, "architecture": "64-bit", "computer_name": "DESKTOP"},
            "collected_at": "10:05",
        }

        self.app._display_diagnostics(first_payload)
        self.app.update_idletasks()

        initial_children = {
            "cpu": len(self.app.cpu_card.inner_frame.winfo_children()),
            "ram": len(self.app.ram_card.inner_frame.winfo_children()),
            "ssd": len(self.app.storage_card.inner_frame.winfo_children()),
            "system": len(self.app.system_card.inner_frame.winfo_children()),
        }

        self.app._display_diagnostics(second_payload)
        self.app.update_idletasks()

        refreshed_children = {
            "cpu": len(self.app.cpu_card.inner_frame.winfo_children()),
            "ram": len(self.app.ram_card.inner_frame.winfo_children()),
            "ssd": len(self.app.storage_card.inner_frame.winfo_children()),
            "system": len(self.app.system_card.inner_frame.winfo_children()),
        }

        self.assertEqual(initial_children, refreshed_children)
        self.assertGreater(initial_children["cpu"], 0)
        self.assertGreater(initial_children["ram"], 0)
        self.assertGreater(initial_children["ssd"], 0)
        self.assertGreater(initial_children["system"], 0)
        self.assertEqual(self.app.status_message.cget("text"), "✔ Dados atualizados com sucesso.")


if __name__ == "__main__":
    unittest.main()
