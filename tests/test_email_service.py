import os

from modules import email as email_module
from modules.email_service import EmailService


def test_email_service_formats_bytes_and_generates_subject():
    service = EmailService(api_key="re_test_key", from_email="sender@example.com")

    assert service.format_bytes(1548258741) == "1.44 GB"
    assert service.generate_subject("PC-FINANCEIRO", "16/07/2026") == "Relatório de Manutenção - PC-FINANCEIRO - 16/07/2026"


def test_email_service_validates_configuration_and_masks_key():
    service = EmailService(api_key="re_1234567890abcdef", from_email="sender@example.com")

    assert service.validate_email("sender@example.com") is None
    assert service.validate_email("email-invalido") == "Email inválido."
    assert service.mask_api_key("re_1234567890abcdef") == "re_xxxxx************"


def test_send_report_returns_standard_result(monkeypatch, tmp_path):
    attachment_path = tmp_path / "report.txt"
    attachment_path.write_text("teste", encoding="utf-8")

    class DummyResend:
        api_key = None

        class Emails:
            @staticmethod
            def send(payload):
                return {"id": "resend_123"}

    monkeypatch.setattr(email_module, "resend", DummyResend)

    service = EmailService(api_key="re_test_key", from_email="sender@example.com")
    result = service.send_report("dest@example.com", "Assunto", "Mensagem", str(attachment_path))

    assert result["success"] is True
    assert result["resend_id"] == "resend_123"
    assert result["message"] == "Relatório enviado."


def test_test_send_creates_temp_report_and_cleans_up(monkeypatch, tmp_path):
    class DummyResend:
        api_key = None

        class Emails:
            @staticmethod
            def send(payload):
                return {"id": "resend_456"}

    monkeypatch.setattr(email_module, "resend", DummyResend)

    service = EmailService(api_key="re_test_key", from_email="sender@example.com", settings_path=str(tmp_path / "settings.json"))

    def fake_send_report(*args, **kwargs):
        return {"success": True, "message": "Relatório enviado.", "resend_id": "resend_456"}

    monkeypatch.setattr(service, "send_report", fake_send_report)

    result = service.test_send("dest@example.com", initial_payload={"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}})

    assert result["success"] is True
    assert result["attachment_path"] is None or not os.path.exists(result["attachment_path"])


def test_validate_api_key_rejects_non_resend_format():
    service = EmailService(api_key="abc123", from_email="sender@example.com")
    assert service.validate_api_key("abc123") is not None
    assert "re_" in service.validate_api_key("abc123")


def test_send_report_uses_http_when_resend_library_missing(monkeypatch, tmp_path):
    attachment_path = tmp_path / "report.txt"
    attachment_path.write_text("teste", encoding="utf-8")

    monkeypatch.setattr(email_module, "resend", None)

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"id": "resend_http"}'

    def fake_urlopen(request, timeout=5):
        return DummyResponse()

    monkeypatch.setattr(email_module, "urlopen", fake_urlopen)

    service = EmailService(api_key="re_test_key", from_email="sender@example.com")
    monkeypatch.setattr(service, "check_internet", lambda timeout=5: True)

    result = service.send_report("dest@example.com", "Assunto", "Mensagem", str(attachment_path))

    assert result["success"] is True
    assert result["resend_id"] == "resend_http"


def test_http_send_sets_browser_user_agent(monkeypatch, tmp_path):
    attachment_path = tmp_path / "report.txt"
    attachment_path.write_text("teste", encoding="utf-8")

    monkeypatch.setattr(email_module, "resend", None)

    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"id": "user_agent_ok"}'

    def fake_urlopen(request, timeout=5):
        captured["headers"] = dict(request.header_items())
        captured["url"] = request.full_url
        return DummyResponse()

    monkeypatch.setattr(email_module, "urlopen", fake_urlopen)

    service = EmailService(api_key="re_test_key", from_email="sender@example.com")
    monkeypatch.setattr(service, "check_internet", lambda timeout=5: True)

    result = service.send_report("dest@example.com", "Assunto", "Mensagem", str(attachment_path))

    assert result["success"] is True
    assert "User-agent" in captured["headers"]
    assert "Mozilla/5.0" in captured["headers"]["User-agent"]


def test_send_report_uses_backup_api_key_when_primary_fails(monkeypatch, tmp_path):
    attachment_path = tmp_path / "report.txt"
    attachment_path.write_text("teste", encoding="utf-8")

    class DummyResend:
        api_key = None
        used_keys = []

        class Emails:
            @staticmethod
            def send(payload):
                DummyResend.used_keys.append(DummyResend.api_key)
                if DummyResend.api_key == "re_primary_key":
                    raise RuntimeError("primary failed")
                return {"id": "resend_backup"}

    monkeypatch.setattr(email_module, "resend", DummyResend)

    service = EmailService(
        api_key="re_primary_key",
        from_email="sender@example.com",
        recipient_email="dest@example.com",
        settings_path=str(tmp_path / "settings.json"),
    )
    service.backup_api_key = "re_backup_key"
    monkeypatch.setattr(service, "check_internet", lambda timeout=5: True)

    result = service.send_report("dest@example.com", "Assunto", "Mensagem", str(attachment_path))

    assert result["success"] is True
    assert result["resend_id"] == "resend_backup"
    assert DummyResend.used_keys == ["re_primary_key", "re_backup_key"]


def test_send_report_saves_pending_file_when_all_keys_fail(monkeypatch, tmp_path):
    attachment_path = tmp_path / "report.txt"
    attachment_path.write_text("teste", encoding="utf-8")

    class DummyResend:
        api_key = None

        class Emails:
            @staticmethod
            def send(payload):
                raise RuntimeError("fail")

    monkeypatch.setattr(email_module, "resend", DummyResend)

    service = EmailService(
        api_key="re_primary_key",
        from_email="sender@example.com",
        recipient_email="dest@example.com",
        settings_path=str(tmp_path / "settings.json"),
    )
    service.backup_api_key = "re_backup_key"
    service.save_pending_on_failure = True
    service.pending_reports_dir = str(tmp_path / "pending")
    monkeypatch.setattr(service, "check_internet", lambda timeout=5: True)

    result = service.send_report("dest@example.com", "Assunto", "Mensagem", str(attachment_path))

    assert result["success"] is False
    assert result.get("queued") is True
    assert len(list((tmp_path / "pending").glob("*.json"))) == 1
