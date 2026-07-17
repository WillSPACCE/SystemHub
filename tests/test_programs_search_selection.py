import main


def test_program_search_filters_and_selects_installed_program(monkeypatch):
    app = main.App()
    app.withdraw()
    try:
        monkeypatch.setattr(
            main.InstalledProgramsService,
            "get_installed_programs",
            lambda: [
                {
                    "name": "Google Chrome",
                    "version": "1.0",
                    "uninstall_string": "cmd /c uninstall",
                    "install_location": "C:/Program Files/Google/Chrome",
                }
            ],
        )

        app._load_installed_programs()
        app.programs_filter_var.set("chrome")
        app._apply_programs_filter()

        assert len(app.programs_vars) == 1
        app._toggle_program_selection("Google Chrome", app.programs_vars["Google Chrome"])
        assert "Google Chrome" in app.selected_programs_for_report
    finally:
        app.destroy()
