import os
import platform
import re
from typing import Any, Dict, List

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


class CpuService:
    def collect(self, snapshot: Dict[str, Any], system_data: Dict[str, Any]) -> Dict[str, Any]:
        host_cpu = snapshot.get("cpu", {}) or {}
        sensors = snapshot.get("sensors", []) or []
        cpu_data: Dict[str, Any] = {
            "name": self._safe_text(host_cpu.get("name"), "Não suportado pelo dispositivo."),
            "manufacturer": "Não suportado pelo dispositivo.",
            "architecture": system_data.get("architecture", "Não suportado pelo dispositivo."),
            "clock_current": self._safe_text(host_cpu.get("clock_current"), "Não suportado pelo dispositivo."),
            "clock_max": self._safe_text(host_cpu.get("clock_max"), "Não suportado pelo dispositivo."),
            "clock_per_core": [],
            "usage": self._safe_text(host_cpu.get("usage"), "Não suportado pelo dispositivo."),
            "usage_per_core": self._normalize_list(host_cpu.get("usage_per_core")),
            "physical_cores": "Não suportado pelo dispositivo.",
            "threads": "Não suportado pelo dispositivo.",
            "temperature": self._safe_text(host_cpu.get("temperature"), "Não suportado pelo dispositivo."),
            "temperature_per_core": [],
            "power": "Não suportado pelo dispositivo.",
        }

        info = self._get_wmi_cpu_info()
        if info:
            cpu_data["manufacturer"] = self._safe_text(info.get("manufacturer"), cpu_data["manufacturer"])
            cpu_data["architecture"] = self._safe_text(info.get("architecture"), cpu_data["architecture"])
            cpu_data["physical_cores"] = self._safe_text(info.get("physical_cores"), cpu_data["physical_cores"])
            cpu_data["threads"] = self._safe_text(info.get("threads"), cpu_data["threads"])
            if info.get("clock_current"):
                cpu_data["clock_current"] = self._safe_text(info.get("clock_current"), cpu_data["clock_current"])
            if info.get("clock_max"):
                cpu_data["clock_max"] = self._safe_text(info.get("clock_max"), cpu_data["clock_max"])

        temperature_candidates: List[Dict[str, Any]] = []
        for sensor in sensors:
            sensor_type = str(sensor.get("sensor_type", "")).lower()
            name = str(sensor.get("sensor", "")).lower()
            value = sensor.get("value")
            if sensor_type == "temperature" and value is not None and str(value).strip() != "":
                temperature_candidates.append({"name": self._safe_text(sensor.get("sensor"), "Sensor"), "value": value})
            elif sensor_type == "load" and value is not None and str(value).strip() != "":
                current_usage = self._extract_numeric_value(value)
                if current_usage is None:
                    continue
                if self._is_aggregate_load_sensor(name):
                    cpu_data["usage"] = f"{current_usage:.1f}%"
                else:
                    cpu_data["usage_per_core"].append(f"{sensor.get('sensor', 'Sensor')}: {current_usage:.1f}%")
            elif sensor_type == "power" and value is not None and str(value).strip() != "":
                cpu_data["power"] = value

        if temperature_candidates:
            preferred_temperature = self._select_preferred_temperature(temperature_candidates)
            cpu_data["temperature"] = preferred_temperature["value"]
            cpu_data["temperature_per_core"] = [f"{entry['name']}: {entry['value']}" for entry in temperature_candidates]

        return cpu_data

    def _get_wmi_cpu_info(self) -> Dict[str, Any]:
        try:
            logical_cores = None
            physical_cores = None
            if psutil is not None:
                try:
                    logical_cores = psutil.cpu_count(logical=True)
                    physical_cores = psutil.cpu_count(logical=False)
                except Exception:
                    pass
            if logical_cores is None:
                logical_cores = os.cpu_count()
            if physical_cores is None:
                physical_cores = logical_cores

            processor_name = os.environ.get("PROCESSOR_IDENTIFIER") or os.environ.get("PROCESSOR_NAME") or platform.machine()
            return {
                "name": processor_name or None,
                "manufacturer": "Não suportado pelo dispositivo.",
                "architecture": self._format_architecture(platform.machine()),
                "physical_cores": physical_cores,
                "threads": logical_cores,
                "clock_current": None,
                "clock_max": None,
            }
        except Exception:
            return {}
        return {}

    def _format_architecture(self, value: Any) -> str:
        mapping = {0: "x86", 1: "MIPS", 2: "Alpha", 3: "PowerPC", 5: "ARM", 9: "x64", 12: "ARM64"}
        if value in mapping:
            return mapping[value]
        return str(value) if value is not None else "Não suportado pelo dispositivo."

    @staticmethod
    def _extract_numeric_value(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        return float(match.group(0))

    @staticmethod
    def _is_aggregate_load_sensor(sensor_name: str) -> bool:
        name = (sensor_name or "").lower()
        if not name:
            return False
        if any(token in name for token in ("core", "thread", "logical", "per-core")):
            return False
        return any(token in name for token in ("total", "package", "overall", "system")) or ("cpu" in name and ("load" in name or "usage" in name))

    @staticmethod
    def _select_preferred_temperature(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not candidates:
            return {"name": "Sensor", "value": "Não suportado pelo dispositivo."}

        def score(entry: Dict[str, Any]) -> int:
            name = str(entry.get("name", "")).lower()
            if not name:
                return 0
            score_value = 0
            if "package" in name:
                score_value += 5
            if "cpu" in name:
                score_value += 2
            if any(token in name for token in ("core", "thread", "die", "module")):
                score_value -= 3
            return score_value

        return max(candidates, key=score)

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback

    def _normalize_list(self, values: Any) -> List[str]:
        if not values:
            return []
        if isinstance(values, list):
            return [self._safe_text(item, "Não suportado pelo dispositivo.") for item in values]
        return [self._safe_text(values, "Não suportado pelo dispositivo.")]
