import os
from typing import Any, Dict, List

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


class DiskService:
    def collect(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        disks: List[Dict[str, Any]] = []
        if psutil is not None:
            for partition in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        "name": partition.device.rstrip("\\"),
                        "model": "Não suportado pelo dispositivo.",
                        "manufacturer": "Não suportado pelo dispositivo.",
                        "type": self._infer_type(partition.fstype),
                        "serial_number": "Não suportado pelo dispositivo.",
                        "interface": "Não suportado pelo dispositivo.",
                        "firmware": "Não suportado pelo dispositivo.",
                        "total": self._format_gb(usage.total),
                        "used": self._format_gb(usage.used),
                        "free": self._format_gb(usage.free),
                        "filesystem": partition.fstype or "Não suportado pelo dispositivo.",
                        "temperature": "Não suportado pelo dispositivo.",
                        "smart_health": "Não suportado pelo dispositivo.",
                        "remaining_life": "Não suportado pelo dispositivo.",
                        "power_on_hours": "Não suportado pelo dispositivo.",
                        "startup_count": "Não suportado pelo dispositivo.",
                        "reallocated_sectors": "Não suportado pelo dispositivo.",
                        "pending_sectors": "Não suportado pelo dispositivo.",
                        "crc_errors": "Não suportado pelo dispositivo.",
                        "wear_level": "Não suportado pelo dispositivo.",
                        "errors": "Não suportado pelo dispositivo.",
                        "host_writes": "Não suportado pelo dispositivo.",
                        "host_reads": "Não suportado pelo dispositivo.",
                    })
                except Exception:
                    continue

        host_disks = snapshot.get("disks", []) or []
        if host_disks:
            for host_disk in host_disks:
                name = self._safe_text(host_disk.get("name"), "Disco")
                existing = next((item for item in disks if item.get("name", "").lower() == name.lower()), None)
                if existing is None:
                    disks.append({
                        "name": name,
                        "model": self._safe_text(host_disk.get("model"), "Não suportado pelo dispositivo."),
                        "manufacturer": "Não suportado pelo dispositivo.",
                        "type": self._safe_text(host_disk.get("type"), "Não suportado pelo dispositivo."),
                        "serial_number": "Não suportado pelo dispositivo.",
                        "interface": "Não suportado pelo dispositivo.",
                        "firmware": "Não suportado pelo dispositivo.",
                        "total": self._safe_text(host_disk.get("total"), "Não suportado pelo dispositivo."),
                        "used": self._safe_text(host_disk.get("used"), "Não suportado pelo dispositivo."),
                        "free": self._safe_text(host_disk.get("free"), "Não suportado pelo dispositivo."),
                        "filesystem": "Não suportado pelo dispositivo.",
                        "temperature": self._safe_text(host_disk.get("temperature"), "Não suportado pelo dispositivo."),
                        "smart_health": self._safe_text(host_disk.get("smart_health"), "Não suportado pelo dispositivo."),
                        "remaining_life": self._safe_text(host_disk.get("remaining_life"), "Não suportado pelo dispositivo."),
                        "power_on_hours": self._safe_text(host_disk.get("power_on_hours"), "Não suportado pelo dispositivo."),
                        "startup_count": "Não suportado pelo dispositivo.",
                        "reallocated_sectors": "Não suportado pelo dispositivo.",
                        "pending_sectors": "Não suportado pelo dispositivo.",
                        "crc_errors": "Não suportado pelo dispositivo.",
                        "wear_level": "Não suportado pelo dispositivo.",
                        "errors": "Não suportado pelo dispositivo.",
                        "host_writes": "Não suportado pelo dispositivo.",
                        "host_reads": "Não suportado pelo dispositivo.",
                    })
                    continue
                existing["temperature"] = self._safe_text(host_disk.get("temperature"), existing.get("temperature", "Não suportado pelo dispositivo."))
                existing["smart_health"] = self._safe_text(host_disk.get("smart_health"), existing.get("smart_health", "Não suportado pelo dispositivo."))
                existing["remaining_life"] = self._safe_text(host_disk.get("remaining_life"), existing.get("remaining_life", "Não suportado pelo dispositivo."))
                existing["power_on_hours"] = self._safe_text(host_disk.get("power_on_hours"), existing.get("power_on_hours", "Não suportado pelo dispositivo."))

        return disks

    def _infer_type(self, fstype: str) -> str:
        if not fstype:
            return "Não suportado pelo dispositivo."
        return fstype

    def _format_gb(self, value: Any) -> str:
        if value is None or value <= 0:
            return "Não suportado pelo dispositivo."
        return f"{value / (1024 ** 3):.2f} GB"

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback
