import json
import os
from typing import Any, Dict, Optional


class ReportSettingsManager:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "report_settings.json"))

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {
                "auto_send": False,
                "resend_api_key": "",
                "backup_api_key": "",
                "recipient_email": "",
                "from_email": "onboarding@resend.dev",
                "email_subject_template": "Relatório de Manutenção - {computer_name} - {date}",
                "email_body_template": "Olá.\n\nSegue em anexo o relatório de manutenção gerado automaticamente pelo InfoCase Checkup.\n\nComputador: {computer_name}\nUsuário: {user}\nWindows: {os_name}\nVersão: {version}\nData: {date}\nHora: {time}\nEspaço Recuperado: {recovered_human}\n\nO relatório completo encontra-se em anexo.\nMensagem enviada automaticamente pelo InfoCase Checkup.\nINFOCASE TECNOLOGIA",
                "save_pending_on_failure": True,
            }
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
                if isinstance(payload, dict):
                    return {
                        "auto_send": bool(payload.get("auto_send", False)),
                        "resend_api_key": str(payload.get("resend_api_key", "")),
                        "backup_api_key": str(payload.get("backup_api_key", "")),
                        "recipient_email": str(payload.get("recipient_email", "")),
                        "from_email": str(payload.get("from_email", "onboarding@resend.dev")),
                        "email_subject_template": str(payload.get("email_subject_template", "Relatório de Manutenção - {computer_name} - {date}")),
                        "email_body_template": str(payload.get("email_body_template", "Olá.\n\nSegue em anexo o relatório de manutenção gerado automaticamente pelo InfoCase Checkup.\n\nComputador: {computer_name}\nUsuário: {user}\nWindows: {os_name}\nVersão: {version}\nData: {date}\nHora: {time}\nEspaço Recuperado: {recovered_human}\n\nO relatório completo encontra-se em anexo.\nMensagem enviada automaticamente pelo InfoCase Checkup.\nINFOCASE TECNOLOGIA")),
                        "save_pending_on_failure": bool(payload.get("save_pending_on_failure", True)),
                    }
        except Exception:
            pass
        return {
            "auto_send": False,
            "resend_api_key": "",
            "backup_api_key": "",
            "recipient_email": "",
            "from_email": "onboarding@resend.dev",
            "email_subject_template": "Relatório de Manutenção - {computer_name} - {date}",
            "email_body_template": "Olá.\n\nSegue em anexo o relatório de manutenção gerado automaticamente pelo InfoCase Checkup.\n\nComputador: {computer_name}\nUsuário: {user}\nWindows: {os_name}\nVersão: {version}\nData: {date}\nHora: {time}\nEspaço Recuperado: {recovered_human}\n\nO relatório completo encontra-se em anexo.\nMensagem enviada automaticamente pelo InfoCase Checkup.\nINFOCASE TECNOLOGIA",
            "save_pending_on_failure": True,
        }

    def save(self, settings: Dict[str, Any]) -> None:
        payload = {
            "auto_send": bool(settings.get("auto_send", False)),
            "resend_api_key": str(settings.get("resend_api_key", "")),
            "backup_api_key": str(settings.get("backup_api_key", "")),
            "recipient_email": str(settings.get("recipient_email", "")),
            "from_email": str(settings.get("from_email", "onboarding@resend.dev")),
            "email_subject_template": str(settings.get("email_subject_template", "Relatório de Manutenção - {computer_name} - {date}")),
            "email_body_template": str(settings.get("email_body_template", "Olá.\n\nSegue em anexo o relatório de manutenção gerado automaticamente pelo InfoCase Checkup.\n\nComputador: {computer_name}\nUsuário: {user}\nWindows: {os_name}\nVersão: {version}\nData: {date}\nHora: {time}\nEspaço Recuperado: {recovered_human}\n\nO relatório completo encontra-se em anexo.\nMensagem enviada automaticamente pelo InfoCase Checkup.\nINFOCASE TECNOLOGIA")),
            "save_pending_on_failure": bool(settings.get("save_pending_on_failure", True)),
        }
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
