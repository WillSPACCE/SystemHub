import unittest
from unittest.mock import patch

from modules.firewall import FirewallManager
from main import App


class FirewallEncodingTests(unittest.TestCase):
    @patch("modules.firewall.subprocess.run")
    def test_allow_port_uses_utf8_safe_subprocess_settings(self, mock_run):
        mock_run.return_value = type(
            "Result",
            (),
            {"returncode": 0, "stdout": "", "stderr": ""},
        )()

        manager = FirewallManager()
        manager._is_windows = True
        manager.allow_port(8080)

        self.assertTrue(mock_run.called)
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")

    @patch("modules.firewall.subprocess.run")
    def test_allow_port_accepts_direction_and_sets_dir_flag(self, mock_run):
        mock_run.return_value = type(
            "Result",
            (object,),
            {"returncode": 0, "stdout": "", "stderr": ""},
        )()

        manager = FirewallManager()
        manager._is_windows = True
        manager.allow_port(8080, direction="Saída")

        self.assertTrue(mock_run.called)
        args = mock_run.call_args.args[0]
        self.assertIn("dir=out", args)
        self.assertIn("localport=8080", args)

    def test_sort_firewall_rows_prioritizes_port_based_entries(self):
        rows = [
            {"local_addr": "192.168.1.10", "local_port": "", "process": "svc-a"},
            {"local_addr": "127.0.0.1", "local_port": "3050", "process": "app"},
            {"local_addr": "10.0.0.5", "local_port": "8080", "process": "web"},
        ]

        sorted_rows = App._sort_firewall_rows(rows)

        self.assertEqual(sorted_rows[0]["local_port"], "3050")
        self.assertEqual(sorted_rows[1]["local_port"], "8080")
        self.assertEqual(sorted_rows[2]["local_port"], "")

    @patch("modules.firewall.subprocess.run")
    def test_allow_program_creates_rule_without_specific_port(self, mock_run):
        mock_run.return_value = type(
            "Result",
            (object,),
            {"returncode": 0, "stdout": "", "stderr": ""},
        )()

        manager = FirewallManager()
        manager._is_windows = True
        program_path = r"C:\Apps\demo\app.exe"
        manager.allow_program(program_path, direction="Entrada")

        self.assertTrue(mock_run.called)
        args = mock_run.call_args.args[0]
        self.assertIn(f"program={program_path}", args)
        self.assertNotIn("localport=", args)

    def test_firewall_search_text_includes_program_name_and_port(self):
        row = {
            "local_port": "3050",
            "process": "app.exe",
            "program": r"C:\Apps\demo\app.exe",
            "name": "PythonUtilityProgram_app.exe_in",
        }

        search_text = App._build_firewall_search_text(row)

        self.assertIn("app.exe", search_text)
        self.assertIn("3050", search_text)


if __name__ == "__main__":
    unittest.main()
