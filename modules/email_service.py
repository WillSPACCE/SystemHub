import base64
import os
from typing import Any, Dict, Optional

try:
    import resend
except Exception:  # pragma: no cover
    resend = None


class ResendEmailService:
    def __init__(self, api_key: Optional[str] = None, from_email: Optional[str] = None):
        self.api_key = api_key or os.environ.get("RESEND_API_KEY")
        self.from_email = from_email or os.environ.get("RESEND_FROM_EMAIL") or "onboarding@resend.dev"

    def send_report(self, recipient_email: str, subject: str, body: str, attachment_path: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("API key da Resend não configurada.")
        if resend is None:
            raise RuntimeError("Biblioteca resend não está instalada.")
        if not recipient_email:
            raise RuntimeError("Email destinatário não informado.")
        if not os.path.exists(attachment_path):
            raise RuntimeError("Anexo não encontrado.")

        resend.api_key = self.api_key
        payload = self._build_payload(recipient_email, subject, body, attachment_path)
        return resend.Emails.send(payload)

    def _build_payload(self, recipient_email: str, subject: str, body: str, attachment_path: str) -> Dict[str, Any]:
        with open(attachment_path, "rb") as handle:
            attachment_content = handle.read()
        return {
            "from": self.from_email,
            "to": [recipient_email],
            "subject": subject,
            "text": body,
            "attachments": [{"filename": os.path.basename(attachment_path), "content": base64.b64encode(attachment_content).decode("ascii")}],
        }
