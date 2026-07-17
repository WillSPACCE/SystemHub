import base64
import json
import os
import re
import socket
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from modules.settings import ReportSettingsManager

try:
    import resend
except Exception:  # pragma: no cover
    resend = None


DEFAULT_SUBJECT_TEMPLATE = "Relatório de Manutenção - {computer_name} - {date}"
DEFAULT_BODY_TEMPLATE = (
    "Olá.\n\n"
    "Segue em anexo o relatório de manutenção gerado automaticamente pelo InfoCase Checkup.\n\n"
    "Computador: {computer_name}\n"
    "Usuário: {user}\n"
    "Windows: {os_name}\n"
    "Versão: {version}\n"
    "Data: {date}\n"
    "Hora: {time}\n"
    "Espaço Recuperado: {recovered_human}\n\n"
    "O relatório completo encontra-se em anexo.\n"
    "Mensagem enviada automaticamente pelo InfoCase Checkup.\n"
    "INFOCASE TECNOLOGIA"
)


class EmailService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        recipient_email: Optional[str] = None,
        auto_send: Optional[bool] = None,
        settings_path: Optional[str] = None,
        settings_manager: Optional[ReportSettingsManager] = None,
    ) -> None:
        self.settings_path = settings_path or os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "report_settings.json"))
        self.settings_manager = settings_manager or ReportSettingsManager(path=self.settings_path)
        self.log_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "email.log"))
        self.pending_reports_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "pending_reports"))
        self.config = self.load_config()
        self.api_key = api_key or self.config.get("resend_api_key") or os.environ.get("RESEND_API_KEY") or ""
        self.backup_api_key = self.config.get("backup_api_key") or ""
        self.from_email = from_email or self.config.get("from_email") or os.environ.get("RESEND_FROM_EMAIL") or "onboarding@resend.dev"
        self.recipient_email = recipient_email or self.config.get("recipient_email") or ""
        self.auto_send = bool(auto_send if auto_send is not None else self.config.get("auto_send", False))
        self.email_subject_template = self.config.get("email_subject_template") or DEFAULT_SUBJECT_TEMPLATE
        self.email_body_template = self.config.get("email_body_template") or DEFAULT_BODY_TEMPLATE
        self.save_pending_on_failure = bool(self.config.get("save_pending_on_failure", True))
        self.last_status = None
        self.last_error = None
        self.last_resend_id = None

    def load_config(self) -> Dict[str, Any]:
        payload = self.settings_manager.load()
        return {
            "auto_send": bool(payload.get("auto_send", False)),
            "resend_api_key": str(payload.get("resend_api_key", "")),
            "backup_api_key": str(payload.get("backup_api_key", "")),
            "recipient_email": str(payload.get("recipient_email", "")),
            "from_email": str(payload.get("from_email", "onboarding@resend.dev")),
            "email_subject_template": str(payload.get("email_subject_template", DEFAULT_SUBJECT_TEMPLATE)),
            "email_body_template": str(payload.get("email_body_template", DEFAULT_BODY_TEMPLATE)),
            "save_pending_on_failure": bool(payload.get("save_pending_on_failure", True)),
        }

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "auto_send": bool((config or {}).get("auto_send", self.auto_send)),
            "resend_api_key": str((config or {}).get("resend_api_key", self.api_key or "")),
            "backup_api_key": str((config or {}).get("backup_api_key", self.backup_api_key or "")),
            "recipient_email": str((config or {}).get("recipient_email", self.recipient_email or "")),
            "from_email": str((config or {}).get("from_email", self.from_email or "onboarding@resend.dev")),
            "email_subject_template": str((config or {}).get("email_subject_template", self.email_subject_template or DEFAULT_SUBJECT_TEMPLATE)),
            "email_body_template": str((config or {}).get("email_body_template", self.email_body_template or DEFAULT_BODY_TEMPLATE)),
            "save_pending_on_failure": bool((config or {}).get("save_pending_on_failure", self.save_pending_on_failure)),
        }
        self.settings_manager.save(payload)
        self.config = payload
        self.api_key = payload.get("resend_api_key", "")
        self.backup_api_key = payload.get("backup_api_key", "")
        self.from_email = payload.get("from_email", "onboarding@resend.dev")
        self.recipient_email = payload.get("recipient_email", "")
        self.auto_send = bool(payload.get("auto_send", False))
        self.email_subject_template = payload.get("email_subject_template") or DEFAULT_SUBJECT_TEMPLATE
        self.email_body_template = payload.get("email_body_template") or DEFAULT_BODY_TEMPLATE
        self.save_pending_on_failure = bool(payload.get("save_pending_on_failure", True))
        return payload

    def validate_email(self, email: Optional[str]) -> Optional[str]:
        value = (email or "").strip()
        if not value:
            return "Email obrigatório."
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            return "Email inválido."
        return None

    def validate_api_key(self, api_key: Optional[str] = None) -> Optional[str]:
        value = (api_key or self.api_key or "").strip()
        if not value:
            return "API Key Resend não configurada."
        if not value.startswith("re_"):
            return "API Key Resend inválida. O formato esperado começa com 're_'."
        return None

    def format_bytes(self, value: Any) -> str:
        try:
            size = float(value or 0)
        except (TypeError, ValueError):
            size = 0.0
        units = ["B", "KB", "MB", "GB", "TB"]
        current = size
        unit_index = 0
        while current >= 1024 and unit_index < len(units) - 1:
            current /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(size)} {units[0]}"
        text = f"{current:.2f}".rstrip("0").rstrip(".")
        return f"{text} {units[unit_index]}"

    def generate_subject(self, computer_name: str, report_date: Optional[str] = None) -> str:
        date_text = report_date or datetime.now().strftime("%d/%m/%Y")
        return self.render_subject(computer_name, report_date=date_text)

    def render_subject(self, computer_name: str, report_date: Optional[str] = None) -> str:
        date_text = report_date or datetime.now().strftime("%d/%m/%Y")
        context = {"computer_name": computer_name or "Sistema", "date": date_text}
        return self._render_template(self.email_subject_template or DEFAULT_SUBJECT_TEMPLATE, context)

    def generate_body(
        self,
        initial_payload: Dict[str, Any],
        report_path: str,
        recovered_bytes: int,
        report_date: Optional[str] = None,
        report_time: Optional[str] = None,
    ) -> str:
        system = initial_payload.get("system", {}) or {}
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "Não disponível"
        computer = system.get("computer_name", "Não disponível")
        os_name = system.get("os_name", "Não disponível")
        version = system.get("version") or initial_payload.get("program_version") or "Não disponível"
        date_text = report_date or datetime.now().strftime("%d/%m/%Y")
        time_text = report_time or datetime.now().strftime("%H:%M:%S")
        recovered_text = self.format_bytes(recovered_bytes)
        context = {
            "computer_name": computer,
            "user": user,
            "os_name": os_name,
            "version": version,
            "date": date_text,
            "time": time_text,
            "recovered_bytes": recovered_bytes,
            "recovered_human": recovered_text,
        }
        return self._render_template(self.email_body_template or DEFAULT_BODY_TEMPLATE, context)

    def send_report(self, recipient_email: str, subject: str, body: str, attachment_path: str, timeout: int = 30, allow_queue: bool = True) -> Dict[str, Any]:
        recipient = (recipient_email or self.recipient_email or "").strip()
        from_email = (self.from_email or "").strip()
        api_key = (self.api_key or "").strip()

        validation_error = self.validate_api_key(api_key)
        if validation_error:
            self._record_log(recipient, "erro", validation_error)
            return {"success": False, "message": validation_error}

        if not from_email:
            message = "Email remetente não configurado."
            self._record_log(recipient, "erro", message)
            return {"success": False, "message": message}

        email_error = self.validate_email(recipient)
        if email_error:
            self._record_log(recipient, "erro", email_error)
            return {"success": False, "message": email_error}

        if not os.path.exists(attachment_path):
            message = "Anexo não encontrado."
            self._record_log(recipient, "erro", message)
            return {"success": False, "message": message}

        if not self.check_internet(timeout=min(timeout, 5)):
            message = "Sem conexão."
            if allow_queue and self.save_pending_on_failure:
                self._queue_pending_report(recipient, subject, body, attachment_path, from_email, [api_key, self.backup_api_key], message)
                self._record_log(recipient, "pendente", message)
                return {"success": False, "message": "Sem conexão. Relatório salvo para envio posterior.", "queued": True}
            self._record_log(recipient, "offline", message)
            return {"success": False, "message": message}

        last_error = None
        for current_api_key in [api_key, self.backup_api_key]:
            if not current_api_key:
                continue
            try:
                payload = self._build_payload(recipient, subject, body, attachment_path)
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(timeout)
                try:
                    response = self._send_via_resend(payload, current_api_key, timeout)
                finally:
                    socket.setdefaulttimeout(old_timeout)
                resend_id = response.get("id") if isinstance(response, dict) else None
                self._record_log(recipient, "enviado", None, resend_id=resend_id)
                return {"success": True, "message": "Relatório enviado.", "resend_id": resend_id, "api_key_used": current_api_key}
            except socket.timeout:
                last_error = "Tempo limite excedido ao enviar o e-mail."
            except Exception as exc:  # pragma: no cover - defensive fallback
                last_error = str(exc) or "Falha ao enviar o e-mail."

        if allow_queue and self.save_pending_on_failure:
            self._queue_pending_report(recipient, subject, body, attachment_path, from_email, [api_key, self.backup_api_key], last_error or "Falha ao enviar o e-mail.")
            self._record_log(recipient, "pendente", last_error or "Falha ao enviar o e-mail.")
            return {"success": False, "message": "Falha ao enviar. Relatório salvo para envio posterior.", "queued": True, "error": last_error}

        self._record_log(recipient, "erro", last_error or "Falha ao enviar o e-mail.")
        return {"success": False, "message": last_error or "Falha ao enviar o e-mail.", "queued": False}

    def test_send(self, recipient_email: Optional[str] = None, initial_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        attachment_path = os.path.join(tempfile.gettempdir(), "Teste_Email.txt")
        payload = initial_payload or {"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}}
        body = self.generate_body(payload, attachment_path, 0, report_date=datetime.now().strftime("%d/%m/%Y"), report_time=datetime.now().strftime("%H:%M:%S"))
        content = (
            "INFOCASE CHECKUP\n"
            "TESTE DE ENVIO\n\n"
            f"Data: {datetime.now().strftime('%d/%m/%Y')}\n"
            f"Hora: {datetime.now().strftime('%H:%M:%S')}\n"
            f"Nome PC: {payload.get('system', {}).get('computer_name', 'Não disponível')}\n"
            f"Usuário: {os.environ.get('USERNAME') or os.environ.get('USER') or 'Não disponível'}\n"
            f"Windows: {payload.get('system', {}).get('os_name', 'Windows')}\n"
            f"Versão: {payload.get('system', {}).get('version', 'Não disponível')}\n\n"
            "Mensagem: Este é um teste de envio do InfoCase Checkup.\n\n"
            f"{body}"
        )
        with open(attachment_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        try:
            result = self.send_report(recipient_email or self.recipient_email or "", "Teste de envio do InfoCase Checkup", content, attachment_path)
            return {**result, "attachment_path": None}
        finally:
            if os.path.exists(attachment_path):
                os.remove(attachment_path)

    def _build_payload(self, recipient_email: str, subject: str, body: str, attachment_path: str) -> Dict[str, Any]:
        with open(attachment_path, "rb") as handle:
            attachment_content = handle.read()
        return {
            "from": self.from_email,
            "to": [recipient_email],
            "subject": subject,
            "text": body,
            "attachments": [
                {
                    "filename": os.path.basename(attachment_path),
                    "content": base64.b64encode(attachment_content).decode("ascii"),
                }
            ],
        }

    def _send_via_resend(self, payload: Dict[str, Any], api_key: str, timeout: int = 30) -> Dict[str, Any]:
        if resend is not None:
            try:
                resend.api_key = api_key
                response = resend.Emails.send(payload)
                if isinstance(response, dict):
                    return response
            except Exception:
                pass

        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Origin": "https://resend.com",
                "Referer": "https://resend.com/",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response_handle:
                response_body = response_handle.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(error_body or str(exc)) from exc
        except URLError as exc:
            raise RuntimeError(str(exc.reason or exc)) from exc

        if not response_body:
            return {}
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(response_body) from exc

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        rendered = template or DEFAULT_BODY_TEMPLATE
        for key, value in context.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        return rendered

    def _queue_pending_report(self, recipient: str, subject: str, body: str, attachment_path: str, from_email: str, api_keys: list[str], reason: Optional[str]) -> None:
        os.makedirs(self.pending_reports_dir, exist_ok=True)
        now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        queue_file = os.path.join(self.pending_reports_dir, f"{now}.txt")
        with open(attachment_path, "rb") as source_handle, open(queue_file, "wb") as target_handle:
            target_handle.write(source_handle.read())
        metadata = {
            "recipient_email": recipient,
            "subject": subject,
            "body": body,
            "attachment_path": queue_file,
            "from_email": from_email,
            "api_keys": [key for key in api_keys if key],
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
        with open(os.path.join(self.pending_reports_dir, f"{now}.json"), "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False)

    def send_pending_reports(self) -> Dict[str, Any]:
        if not os.path.exists(self.pending_reports_dir):
            return {"success": True, "message": "Nenhum relatório pendente.", "sent": 0}
        queue_files = sorted([os.path.join(self.pending_reports_dir, path) for path in os.listdir(self.pending_reports_dir) if path.endswith(".json")])
        sent = 0
        for queue_path in queue_files:
            try:
                with open(queue_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                attachment_path = payload.get("attachment_path") or queue_path.replace(".json", ".txt")
                if not os.path.exists(attachment_path):
                    continue
                result = self.send_report(
                    recipient_email=payload.get("recipient_email", ""),
                    subject=payload.get("subject", "Relatório pendente"),
                    body=payload.get("body", ""),
                    attachment_path=attachment_path,
                    allow_queue=False,
                )
                if result.get("success"):
                    sent += 1
                    os.remove(queue_path)
                    if os.path.exists(attachment_path):
                        os.remove(attachment_path)
            except Exception:
                continue
        return {"success": True, "message": f"Relatórios pendentes processados: {sent}", "sent": sent}

    def _record_log(self, recipient: str, status: str, error: Optional[str] = None, resend_id: Optional[str] = None) -> None:
        self.last_status = status
        self.last_error = error
        self.last_resend_id = resend_id
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} | {recipient or '-'} | {status} | {error or '-'} | {resend_id or '-'}\n")

    def load_recent_history(self, limit: int = 5) -> list[Dict[str, str]]:
        if not os.path.exists(self.log_path):
            return []
        entries: list[Dict[str, str]] = []
        with open(self.log_path, "r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle.readlines() if line.strip()]
        for line in lines[-limit:]:
            parts = [part.strip() for part in line.split("|")]
            if len(parts) >= 5:
                entries.append(
                    {
                        "timestamp": parts[0],
                        "recipient": parts[1],
                        "status": parts[2],
                        "error": parts[3],
                        "resend_id": parts[4],
                    }
                )
        return entries

    def mask_api_key(self, api_key: Optional[str]) -> str:
        value = (api_key or "").strip()
        if not value:
            return ""
        if value.startswith("re_"):
            return "re_xxxxx************"
        return f"{value[:4]}{'*' * max(8, len(value) - 4)}"

    def check_internet(self, timeout: int = 5) -> bool:
        try:
            with urlopen("https://www.google.com", timeout=timeout) as _:
                return True
        except (URLError, TimeoutError, OSError):
            return False


ResendEmailService = EmailService


def build_email_body(initial_payload: Dict[str, Any], report_path: str, recovered_bytes: int) -> str:
    service = EmailService()
    return service.generate_body(initial_payload, report_path, recovered_bytes)
