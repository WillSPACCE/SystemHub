import unittest

from main import App


class DummyEntry:
    def __init__(self):
        self.value = ""

    def delete(self, start, end=None):
        self.value = ""

    def insert(self, index, value):
        self.value = value

    def get(self):
        return self.value

    def winfo_exists(self):
        return True


class DummyCombo:
    def __init__(self):
        self.value = "TCP"

    def set(self, value):
        self.value = value

    def get(self):
        return self.value

    def winfo_exists(self):
        return True


class FirewallFilterResetTests(unittest.TestCase):
    def test_reset_firewall_filters_clears_search_and_protocol(self):
        app = App.__new__(App)
        app.firewall_search = DummyEntry()
        app.protocol_filter = DummyCombo()

        app.firewall_search.insert(0, "8080")
        app.protocol_filter.set("TCP")

        app._reset_firewall_filters()

        self.assertEqual(app.firewall_search.get(), "")
        self.assertEqual(app.protocol_filter.get(), "Todos")

    def test_reset_firewall_filters_clears_filter_field(self):
        app = App.__new__(App)
        app.firewall_search = DummyEntry()
        app.protocol_filter = DummyCombo()
        app.firewall_filter_field = DummyCombo()

        app.firewall_search.insert(0, "8080")
        app.protocol_filter.set("TCP")
        app.firewall_filter_field.set("Porta")

        app._reset_firewall_filters()

        self.assertEqual(app.firewall_search.get(), "")
        self.assertEqual(app.protocol_filter.get(), "Todos")
        self.assertEqual(app.firewall_filter_field.get(), "Todos")


if __name__ == "__main__":
    unittest.main()
