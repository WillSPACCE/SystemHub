import tkinter as tk
import unittest
from unittest.mock import patch

from main import App


class WindowsToolsButtonsTests(unittest.TestCase):
    def test_launch_windows_tool_uses_subprocess_for_native_utilities(self):
        app = App.__new__(App)
        app._append_cleanup_log = lambda message: None

        with patch("subprocess.Popen") as mock_popen:
            App._launch_windows_tool(app, ["cleanmgr.exe"], "Limpeza de disco")

        mock_popen.assert_called_once_with(["cleanmgr.exe"], shell=False)

    def test_action_button_uses_button_like_style(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = App.__new__(App)
            app._font = lambda *args, **kwargs: ("Segoe UI", 10)
            button = app._create_action_button(root, "Abrir", lambda: None)
            self.assertEqual(button.cget("relief"), "raised")
            self.assertEqual(button.cget("bd"), 1)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
