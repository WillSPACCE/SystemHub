import main


def test_cleanup_page_builds_polished_layout_widgets():
    app = main.App()
    app.withdraw()
    try:
        app._build_cleanup_page()

        assert app.cleanup_start_button.winfo_exists()
        assert app.cleanup_reports_button.winfo_exists()
        assert app.cleanup_send_button.winfo_exists()
        assert app.cleanup_options_frame.winfo_exists()
        assert len(app.cleanup_option_cards) > 0
    finally:
        app.destroy()
