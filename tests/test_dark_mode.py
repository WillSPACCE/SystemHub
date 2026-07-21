import unittest
from unittest.mock import Mock

from main import App, get_theme_values


class DarkModeTests(unittest.TestCase):
    def test_dark_theme_has_dark_backgrounds(self):
        theme = get_theme_values("dark")
        self.assertEqual(theme["bg"], "#07111F")
        self.assertEqual(theme["card_bg"], "#0F172A")
        self.assertEqual(theme["text_primary"], "#F8FAFC")

    def test_toggle_theme_switches_to_dark_mode(self):
        app = App.__new__(App)
        app.theme_mode = "light"
        app._apply_theme = Mock()

        app._toggle_theme()

        app._apply_theme.assert_called_once_with("dark")

    def test_light_theme_uses_previous_light_palette(self):
        theme = get_theme_values("light")
        self.assertEqual(theme["bg"], "#F6F8FC")
        self.assertEqual(theme["card_bg"], "#FFFFFF")
        self.assertEqual(theme["text_primary"], "#111827")

    def test_theme_color_reverts_to_light_when_switching_back(self):
        app = App.__new__(App)
        app.theme_mode = "light"
        self.assertEqual(app._theme_color("#0F172A", "background"), "#FFFFFF")
        self.assertEqual(app._theme_color("#94A3B8", "foreground"), "#6B7280")

    def test_resolve_widget_foreground_falls_back_to_readable_text_color(self):
        app = App.__new__(App)
        app.theme_mode = "light"
        app._theme_color = lambda value, option: value
        self.assertEqual(app._resolve_widget_foreground(type("Widget", (), {"keys": lambda self: ["background"], "cget": lambda self, key: "#FFFFFF"})(), "#FFFFFF"), "#111827")


if __name__ == "__main__":
    unittest.main()
