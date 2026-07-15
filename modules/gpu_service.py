from typing import Any, Dict


class GpuService:
    def collect(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        host_gpu = snapshot.get("gpu", {}) or {}
        sensors = snapshot.get("sensors", []) or []
        gpu_data: Dict[str, Any] = {
            "name": self._safe_text(host_gpu.get("name"), "Não suportado pelo dispositivo."),
            "manufacturer": "Não suportado pelo dispositivo.",
            "usage": self._safe_text(host_gpu.get("usage"), "Não suportado pelo dispositivo."),
            "temperature": self._safe_text(host_gpu.get("temperature"), "Não suportado pelo dispositivo."),
            "clock": "Não suportado pelo dispositivo.",
            "dedicated_memory": "Não suportado pelo dispositivo.",
            "used_memory": "Não suportado pelo dispositivo.",
        }

        for sensor in sensors:
            sensor_type = str(sensor.get("sensor_type", "")).lower()
            name = str(sensor.get("sensor", "")).lower()
            value = sensor.get("value")
            if sensor.get("hardware_type", "").lower() in {"gpu", "graphics"}:
                if sensor_type == "load" and value is not None and str(value).strip() != "":
                    gpu_data["usage"] = value
                elif sensor_type == "temperature" and value is not None and str(value).strip() != "":
                    gpu_data["temperature"] = value
                elif sensor_type == "clock" and value is not None and str(value).strip() != "":
                    gpu_data["clock"] = value

        if not gpu_data["name"] or gpu_data["name"] == "Não suportado pelo dispositivo.":
            gpu_data["name"] = self._find_gpu_name(snapshot)

        return gpu_data

    def _find_gpu_name(self, snapshot: Dict[str, Any]) -> str:
        for sensor in snapshot.get("sensors", []) or []:
            if sensor.get("hardware_type", "").lower() in {"gpu", "graphics"}:
                return self._safe_text(sensor.get("hardware"), "Não suportado pelo dispositivo.")
        return "Não suportado pelo dispositivo."

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback
