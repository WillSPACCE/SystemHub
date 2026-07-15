import unittest
from unittest.mock import patch

from modules.firewall import FirewallManager


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


if __name__ == "__main__":
    unittest.main()
