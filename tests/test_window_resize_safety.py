import unittest

import main


class WindowResizeSafetyTest(unittest.TestCase):
    def setUp(self):
        self.app = main.App()
        self.app.withdraw()
        self.app.update_idletasks()

    def tearDown(self):
        if self.app.winfo_exists():
            self.app.destroy()

    def test_canvas_configure_does_not_raise_when_canvas_is_empty(self):
        self.app.page_canvas.delete("all")

        self.app._on_page_canvas_configure()

        self.assertTrue(True)

    def test_layout_dashboard_cards_does_not_raise_when_cards_missing(self):
        for attr in ("dashboard_cards_frame", "cpu_card", "ram_card", "storage_card", "system_card"):
            if hasattr(self.app, attr):
                delattr(self.app, attr)

        self.app._layout_dashboard_cards()

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
