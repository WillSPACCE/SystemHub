from typing import Any, Dict, Optional

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


class MemoryService:
    def collect(self) -> Dict[str, Any]:
        memory_data: Dict[str, Any] = {
            "total": "Não suportado pelo dispositivo.",
            "used": "Não suportado pelo dispositivo.",
            "free": "Não suportado pelo dispositivo.",
            "available": "Não suportado pelo dispositivo.",
            "percent": "Não suportado pelo dispositivo.",
            "speed": "Não suportado pelo dispositivo.",
            "type": "Não suportado pelo dispositivo.",
            "manufacturer": "Não suportado pelo dispositivo.",
            "modules": "Não suportado pelo dispositivo.",
        }

        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                memory_data["total"] = self._format_gb(vm.total)
                memory_data["used"] = self._format_gb(vm.used)
                memory_data["free"] = self._format_gb(vm.available)
                memory_data["available"] = self._format_gb(vm.available)
                memory_data["percent"] = f"{vm.percent:.1f}%"
            except Exception:
                pass

        info = self._get_wmi_memory_info()
        if info:
            memory_data["speed"] = self._safe_text(info.get("speed"), memory_data["speed"])
            memory_data["type"] = self._safe_text(info.get("type"), memory_data["type"])
            memory_data["manufacturer"] = self._safe_text(info.get("manufacturer"), memory_data["manufacturer"])
            memory_data["modules"] = self._safe_text(info.get("modules"), memory_data["modules"])
        return memory_data

    def _get_wmi_memory_info(self) -> Dict[str, Any]:
        try:
            import json
            import subprocess

            command = (
                "Get-CimInstance Win32_PhysicalMemory | "
                "Select-Object Manufacturer,Speed,PartNumber,SerialNumber,Capacity | ConvertTo-Json -Compress"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if completed.returncode != 0:
                return {}
            payload = (completed.stdout or "").strip()
            if not payload:
                return {}

            parsed = json.loads(payload)
            # parsed may be a dict (single module) or a list (multiple modules)
            modules = parsed if isinstance(parsed, list) else [parsed]
            modules = [m for m in modules if isinstance(m, dict)]
            if not modules:
                return {}

            total_modules = len(modules)
            first = modules[0]
            speed = first.get("Speed")
            manufacturer = first.get("Manufacturer")
            part = first.get("PartNumber") or first.get("SerialNumber")
            # capacity may be string/number in bytes
            try:
                capacity_bytes = int(first.get("Capacity") or 0)
            except Exception:
                capacity_bytes = 0

            return {
                "speed": f"{speed}" if speed else None,
                "type": None,
                "manufacturer": manufacturer,
                "modules": total_modules,
                "capacity_bytes": capacity_bytes,
                "part_number": part,
            }
        except Exception:
            return {}

    def _decode_type(self, value: Optional[int]) -> str:
        mapping = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 28: "DDR5"}
        return mapping.get(value, "Não suportado pelo dispositivo.")

    def _format_gb(self, value: Optional[int]) -> str:
        if value is None or value <= 0:
            return "Não suportado pelo dispositivo."
        return f"{value / (1024 ** 3):.2f} GB"

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback
