import json
import os
from typing import Any, Dict, Optional


class ReportSettingsManager:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "report_settings.json"))

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {"auto_send": False, "resend_api_key": "", "recipient_email": "martins.willyan20@gmail.com", "from_email": "onboarding@resend.dev"}
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
                if isinstance(payload, dict):
                    return {
                        "auto_send": bool(payload.get("auto_send", False)),
                        "resend_api_key": str(payload.get("resend_api_key", "")),
                        "recipient_email": str(payload.get("recipient_email", "martins.willyan20@gmail.com")),
                        "from_email": str(payload.get("from_email", "onboarding@resend.dev")),
                    }
        except Exception:
            pass
        return {"auto_send": False, "resend_api_key": "", "recipient_email": "martins.willyan20@gmail.com", "from_email": "onboarding@resend.dev"}

    def save(self, settings: Dict[str, Any]) -> None:
        payload = {
            "auto_send": bool(settings.get("auto_send", False)),
            "resend_api_key": str(settings.get("resend_api_key", "")),
            "recipient_email": str(settings.get("recipient_email", "martins.willyan20@gmail.com")),
            "from_email": str(settings.get("from_email", "onboarding@resend.dev")),
        }
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
