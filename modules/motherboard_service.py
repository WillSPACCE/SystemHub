from typing import Any, Dict


class MotherboardService:
    def collect(self) -> Dict[str, Any]:
        info = self._get_wmi_motherboard_info()
        return {
            "manufacturer": self._safe_text(info.get("manufacturer"), "Não suportado pelo dispositivo."),
            "model": self._safe_text(info.get("model"), "Não suportado pelo dispositivo."),
            "bios": self._safe_text(info.get("bios"), "Não suportado pelo dispositivo."),
            "version": self._safe_text(info.get("version"), "Não suportado pelo dispositivo."),
            "date": self._safe_text(info.get("date"), "Não suportado pelo dispositivo."),
        }

    def _get_wmi_motherboard_info(self) -> Dict[str, Any]:
        try:
            import json
            import subprocess
            command = (
                "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,SerialNumber | "
                "ConvertTo-Json -Compress"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if completed.returncode != 0:
                return {}
            payload = completed.stdout.strip()
            if not payload:
                return {}
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return {
                    "manufacturer": parsed.get("Manufacturer"),
                    "model": parsed.get("Product"),
                    "bios": "Não suportado pelo dispositivo.",
                    "version": "Não suportado pelo dispositivo.",
                    "date": "Não suportado pelo dispositivo.",
                }
        except Exception:
            return {}
        return {}

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback
