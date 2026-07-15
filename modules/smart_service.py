from typing import Any, Dict, List

try:
    from pySMART import DeviceList
except Exception:  # pragma: no cover
    DeviceList = None


class SmartService:
    def collect(self, disks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        smart_devices = self._load_smart_devices()
        updated: List[Dict[str, Any]] = []
        for disk in disks:
            info = self._match_smart_info(disk, smart_devices)
            disk_copy = dict(disk)
            disk_copy["temperature"] = self._normalize_temperature(info.get("temperature"), disk_copy.get("temperature", "Não suportado pelo dispositivo."))
            disk_copy["smart_health"] = self._safe_text(info.get("smart_health"), disk_copy.get("smart_health", "Não suportado pelo dispositivo."))
            disk_copy["remaining_life"] = self._safe_text(info.get("remaining_life"), disk_copy.get("remaining_life", "Não suportado pelo dispositivo."))
            disk_copy["power_on_hours"] = self._safe_text(info.get("power_on_hours"), disk_copy.get("power_on_hours", "Não suportado pelo dispositivo."))
            disk_copy["startup_count"] = self._safe_text(info.get("startup_count"), disk_copy.get("startup_count", "Não suportado pelo dispositivo."))
            disk_copy["reallocated_sectors"] = self._safe_text(info.get("reallocated_sectors"), disk_copy.get("reallocated_sectors", "Não suportado pelo dispositivo."))
            disk_copy["pending_sectors"] = self._safe_text(info.get("pending_sectors"), disk_copy.get("pending_sectors", "Não suportado pelo dispositivo."))
            disk_copy["crc_errors"] = self._safe_text(info.get("crc_errors"), disk_copy.get("crc_errors", "Não suportado pelo dispositivo."))
            disk_copy["wear_level"] = self._safe_text(info.get("wear_level"), disk_copy.get("wear_level", "Não suportado pelo dispositivo."))
            disk_copy["errors"] = self._safe_text(info.get("errors"), disk_copy.get("errors", "Não suportado pelo dispositivo."))
            disk_copy["interface"] = self._safe_text(info.get("interface"), disk_copy.get("interface", "Não suportado pelo dispositivo."))
            disk_copy["firmware"] = self._safe_text(info.get("firmware"), disk_copy.get("firmware", "Não suportado pelo dispositivo."))
            disk_copy["host_writes"] = self._safe_text(info.get("host_writes"), disk_copy.get("host_writes", "Não suportado pelo dispositivo."))
            disk_copy["host_reads"] = self._safe_text(info.get("host_reads"), disk_copy.get("host_reads", "Não suportado pelo dispositivo."))
            updated.append(disk_copy)
        return updated

    def _load_smart_devices(self) -> List[Dict[str, Any]]:
        if DeviceList is None:
            return []
        try:
            devices = DeviceList()
            records: List[Dict[str, Any]] = []
            for device in getattr(devices, "devices", []) or []:
                try:
                    device.update()
                except Exception:
                    pass
                records.append({
                    "name": self._safe_text(getattr(device, "name", None), ""),
                    "model": self._safe_text(getattr(device, "model", None), ""),
                    "serial": self._safe_text(getattr(device, "serial", None), ""),
                    "interface": self._safe_text(getattr(device, "interface", None), ""),
                    "firmware": self._safe_text(getattr(device, "firmware", None), ""),
                    "temperature": self._normalize_temperature(getattr(device, "temperature", None), None),
                    "smart_health": self._normalize_health(getattr(device, "assessment", None)),
                    "capacity": self._safe_text(getattr(device, "capacity", None), ""),
                })
            return records
        except Exception:
            return []

    def _match_smart_info(self, disk: Dict[str, Any], smart_devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not smart_devices:
            return {}
        disk_name = self._safe_text(disk.get("name"), "").lower()
        disk_model = self._safe_text(disk.get("model"), "").lower()
        for device in smart_devices:
            if disk_model and device.get("model", "").lower() and disk_model in device.get("model", "").lower():
                return device
            if disk_name and device.get("name", "").lower() and disk_name in device.get("name", "").lower():
                return device
        return smart_devices[0]

    def _normalize_temperature(self, value: Any, fallback: Any) -> str:
        if value is None:
            return self._safe_text(fallback, "Não suportado pelo dispositivo.")
        if isinstance(value, (int, float)):
            if value in {0, 0.0}:
                return "Não suportado pelo dispositivo."
            return f"{float(value):.0f}°C"
        text = str(value).strip()
        if not text:
            return self._safe_text(fallback, "Não suportado pelo dispositivo.")
        try:
            numeric = float(text)
        except ValueError:
            return self._safe_text(text, self._safe_text(fallback, "Não suportado pelo dispositivo."))
        if numeric in {0, 0.0}:
            return "Não suportado pelo dispositivo."
        return f"{numeric:.0f}°C"

    def _normalize_health(self, value: Any) -> str:
        if value is None:
            return "Não suportado pelo dispositivo."
        text = str(value).strip()
        if not text:
            return "Não suportado pelo dispositivo."
        if text.upper() == "PASS":
            return "100%"
        return text

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback
