import tkinter as tk
import unittest
from unittest.mock import Mock

from main import App


class PageNavigationTests(unittest.TestCase):
    def test_show_page_skips_rerender_for_same_page_when_already_rendered(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = App.__new__(App)
            app.pages = {
                "Dashboard": tk.Frame(root),
                "Ferramentas": tk.Frame(root),
            }
            app.selected_page = "Dashboard"
            app.data = {}
            app._dashboard_needs_refresh = False
            app._info_needs_refresh = False
            app._set_nav_button_active = Mock()
            app._render_dashboard = Mock()
            app._render_info_page = Mock()
            app._handle_window_resize = Mock()
            app.after = lambda delay, callback=None: None
            app._on_page_inner_configure = Mock()
            app.winfo_exists = lambda: True

            app.show_page("Dashboard")
            app.show_page("Dashboard")

            app._render_dashboard.assert_not_called()
            app._render_info_page.assert_not_called()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
