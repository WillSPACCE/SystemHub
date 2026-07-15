import os
import platform
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

try:
    import clr
except ImportError:  # pragma: no cover
    clr = None


def _normalize_value(value: Any, fallback: str = "Não disponível") -> str:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    text = str(value).strip()
    return text if text else fallback


def _format_size_gb(size_bytes: Optional[int]) -> str:
    if not size_bytes:
        return "Não disponível"
    return f"{size_bytes / (1024 ** 3):.2f} GB"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "Não disponível"
    return f"{value:.1f}%"


@dataclass
class CpuData:
    name: str = "Não disponível"
    manufacturer: str = "Não disponível"
    architecture: str = "Não disponível"
    base_frequency_mhz: str = "Não disponível"
    current_frequency_mhz: str = "Não disponível"
    max_frequency_mhz: str = "Não disponível"
    physical_cores: str = "Não disponível"
    logical_cores: str = "Não disponível"
    usage_percent: str = "Não disponível"
    temperature_c: str = "Não disponível"
    max_temperature_c: str = "Não disponível"
    per_core_load: List[str] = field(default_factory=list)
    per_core_clock_mhz: List[str] = field(default_factory=list)
    power_watts: str = "Não disponível"


@dataclass
class MemoryData:
    total_capacity_gb: str = "Não disponível"
    used_capacity_gb: str = "Não disponível"
    free_capacity_gb: str = "Não disponível"
    used_percent: str = "Não disponível"
    speed_mhz: str = "Não disponível"
    type_name: str = "Não disponível"
    manufacturer: str = "Não disponível"
    module_count: str = "Não disponível"


@dataclass
class DiskData:
    name: str = "Não disponível"
    manufacturer: str = "Não disponível"
    model: str = "Não disponível"
    serial_number: str = "Não disponível"
    disk_type: str = "Não disponível"
    total_capacity_gb: str = "Não disponível"
    used_capacity_gb: str = "Não disponível"
    free_capacity_gb: str = "Não disponível"
    file_system: str = "Não disponível"
    drive_letter: str = "Não disponível"
    temperature_c: str = "Não disponível"
    health_percent: str = "Não disponível"
    remaining_life_percent: str = "Não disponível"
    power_on_hours: str = "Não disponível"
    startup_count: str = "Não disponível"
    smart_status: str = "Não disponível"
    smart_warnings: str = "Não disponível"
    reallocated_sectors: str = "Não disponível"
    pending_sectors: str = "Não disponível"
    read_errors: str = "Não disponível"


@dataclass
class GpuData:
    name: str = "Não disponível"
    usage_percent: str = "Não disponível"
    temperature_c: str = "Não disponível"
    dedicated_memory_gb: str = "Não disponível"
    used_memory_gb: str = "Não disponível"
    clock_mhz: str = "Não disponível"


@dataclass
class MotherboardData:
    manufacturer: str = "Não disponível"
    model: str = "Não disponível"
    bios_version: str = "Não disponível"
    bios_date: str = "Não disponível"


@dataclass
class SystemData:
    os_name: str = "Não disponível"
    computer_name: str = "Não disponível"
    version: str = "Não disponível"
    build: str = "Não disponível"
    architecture: str = "Não disponível"
    uptime: str = "Não disponível"


@dataclass
@dataclass
class SensorRecord:
    hardware_name: str = "Não disponível"
    hardware_type: str = "Não disponível"
    sensor_name: str = "Não disponível"
    sensor_type: str = "Não disponível"
    value: str = "Não disponível"


@dataclass
class ComputerHardwareData:
    cpu: CpuData = field(default_factory=CpuData)
    memory: MemoryData = field(default_factory=MemoryData)
    disks: List[DiskData] = field(default_factory=list)
    gpu: GpuData = field(default_factory=GpuData)
    motherboard: MotherboardData = field(default_factory=MotherboardData)
    system: SystemData = field(default_factory=SystemData)
    sensor_records: List[SensorRecord] = field(default_factory=list)
    collected_at: str = "Não disponível"

    def to_text_lines(self) -> List[str]:
        lines: List[str] = []
        lines.append(f"Última atualização: {self.collected_at}")
        lines.append("")
        lines.append("=== CPU ===")
        lines.append(f"Nome: {self.cpu.name}")
        lines.append(f"Fabricante: {self.cpu.manufacturer}")
        lines.append(f"Arquitetura: {self.cpu.architecture}")
        lines.append(f"Frequência base: {self.cpu.base_frequency_mhz}")
        lines.append(f"Frequência atual: {self.cpu.current_frequency_mhz}")
        lines.append(f"Frequência máxima: {self.cpu.max_frequency_mhz}")
        lines.append(f"Núcleos físicos: {self.cpu.physical_cores}")
        lines.append(f"Threads: {self.cpu.logical_cores}")
        lines.append(f"Uso atual: {self.cpu.usage_percent}")
        lines.append(f"Temperatura atual: {self.cpu.temperature_c}")
        lines.append(f"Temperatura máxima: {self.cpu.max_temperature_c}")
        if self.cpu.per_core_load:
            lines.append("Carga por núcleo: " + ", ".join(self.cpu.per_core_load))
        if self.cpu.per_core_clock_mhz:
            lines.append("Clock por núcleo: " + ", ".join(self.cpu.per_core_clock_mhz))
        lines.append(f"Consumo de energia: {self.cpu.power_watts}")
        lines.append("")
        lines.append("=== Memória RAM ===")
        lines.append(f"Capacidade total: {self.memory.total_capacity_gb}")
        lines.append(f"Utilizada: {self.memory.used_capacity_gb}")
        lines.append(f"Livre: {self.memory.free_capacity_gb}")
        lines.append(f"Percentual utilizado: {self.memory.used_percent}")
        lines.append(f"Velocidade: {self.memory.speed_mhz}")
        lines.append(f"Tipo: {self.memory.type_name}")
        lines.append(f"Fabricante: {self.memory.manufacturer}")
        lines.append(f"Módulos instalados: {self.memory.module_count}")
        lines.append("")
        lines.append("=== Armazenamento ===")
        for index, disk in enumerate(self.disks, start=1):
            lines.append(f"Disco {index}: {disk.name}")
            lines.append(f"  Fabricante: {disk.manufacturer}")
            lines.append(f"  Modelo: {disk.model}")
            lines.append(f"  Número de série: {disk.serial_number}")
            lines.append(f"  Tipo: {disk.disk_type}")
            lines.append(f"  Capacidade: {disk.total_capacity_gb}")
            lines.append(f"  Utilizado: {disk.used_capacity_gb}")
            lines.append(f"  Livre: {disk.free_capacity_gb}")
            lines.append(f"  Sistema de arquivos: {disk.file_system}")
            lines.append(f"  Letra da unidade: {disk.drive_letter}")
            lines.append(f"  Temperatura: {disk.temperature_c}")
            lines.append(f"  Saúde: {disk.health_percent}")
            lines.append(f"  Vida útil restante: {disk.remaining_life_percent}")
            lines.append(f"  Horas de funcionamento: {disk.power_on_hours}")
            lines.append(f"  Inicializações: {disk.startup_count}")
            lines.append(f"  Status SMART: {disk.smart_status}")
            lines.append(f"  Avisos SMART: {disk.smart_warnings}")
            lines.append(f"  Setores realocados: {disk.reallocated_sectors}")
            lines.append(f"  Setores pendentes: {disk.pending_sectors}")
            lines.append(f"  Erros de leitura: {disk.read_errors}")
        if not self.disks:
            lines.append("Nenhum disco detectado.")
        lines.append("")
        lines.append("=== Sistema ===")
        lines.append(f"Windows: {self.system.os_name}")
        lines.append(f"Versão: {self.system.version}")
        lines.append(f"Build: {self.system.build}")
        lines.append(f"Arquitetura: {self.system.architecture}")
        lines.append(f"Tempo ligado: {self.system.uptime}")
        lines.append("")
        lines.append("=== Placa-mãe ===")
        lines.append(f"Fabricante: {self.motherboard.manufacturer}")
        lines.append(f"Modelo: {self.motherboard.model}")
        lines.append(f"BIOS: {self.motherboard.bios_version}")
        lines.append(f"Data da BIOS: {self.motherboard.bios_date}")
        lines.append("")
        lines.append("=== GPU ===")
        lines.append(f"Nome: {self.gpu.name}")
        lines.append(f"Uso: {self.gpu.usage_percent}")
        lines.append(f"Temperatura: {self.gpu.temperature_c}")
        lines.append(f"Memória dedicada: {self.gpu.dedicated_memory_gb}")
        lines.append(f"Memória utilizada: {self.gpu.used_memory_gb}")
        lines.append(f"Clock: {self.gpu.clock_mhz}")
        return lines


class _LibreHardwareMonitorAdapter:
    def __init__(self) -> None:
        self._computer: Optional[Any] = None
        self._available = False

    def initialize(self) -> bool:
        if self._available or clr is None:
            return self._available
        try:
            dll_candidates = [
                os.path.join(os.path.dirname(__file__), "LibreHardwareMonitorLib.dll"),
                os.path.join(os.getcwd(), "LibreHardwareMonitorLib.dll"),
                os.path.join(os.path.dirname(__file__), "LibreHardwareMonitor.dll"),
                os.path.join(os.getcwd(), "LibreHardwareMonitor.dll"),
            ]
            for dll in dll_candidates:
                if not dll or not os.path.exists(dll):
                    continue
                try:
                    clr.AddReference(dll)
                    from LibreHardwareMonitor.Hardware import Computer  # type: ignore
                    self._computer = Computer()
                    self._computer.IsCpuEnabled = True
                    self._computer.IsGpuEnabled = True
                    self._computer.IsMemoryEnabled = True
                    self._computer.IsMotherboardEnabled = True
                    self._computer.IsStorageEnabled = True
                    self._computer.IsControllerEnabled = True
                    self._computer.Open()
                    self._available = True
                    return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def iter_hardware(self):
        if not self.initialize():
            return []
        try:
            return list(self._computer.Hardware) if self._computer else []
        except Exception:
            return []

    def update_all_hardware(self) -> None:
        for hardware in self.iter_hardware():
            self._update_hardware_recursive(hardware)

    def _update_hardware_recursive(self, hardware: Any) -> None:
        try:
            hardware.Update()
        except Exception:
            pass
        try:
            for child in list(getattr(hardware, "SubHardware", [])):
                self._update_hardware_recursive(child)
        except Exception:
            pass

    def get_all_sensor_records(self) -> List[SensorRecord]:
        records: List[SensorRecord] = []
        for hardware in self.iter_hardware():
            records.extend(self._collect_hardware_sensors(hardware))
        return records

    def _collect_hardware_sensors(self, hardware: Any) -> List[SensorRecord]:
        records: List[SensorRecord] = []
        try:
            hardware.Update()
        except Exception:
            pass
        hardware_name = _normalize_value(getattr(hardware, "Name", None), "Desconhecido")
        hardware_type = _normalize_value(getattr(getattr(hardware, "HardwareType", None), "ToString", lambda: "")(), "Desconhecido")
        for sensor in list(getattr(hardware, "Sensors", [])):
            try:
                sensor_name = _normalize_value(getattr(sensor, "Name", None), "Desconhecido")
                sensor_type = _normalize_value(getattr(getattr(sensor, "SensorType", None), "ToString", lambda: "")(), "Desconhecido")
                value_raw = getattr(sensor, "Value", None)
                if value_raw is None:
                    continue
                value = f"{float(value_raw):.1f}"
                if sensor_type.lower() == "temperature":
                    value += "°C"
                elif sensor_type.lower() == "load":
                    value += "%"
                elif sensor_type.lower() == "power":
                    value += " W"
                records.append(SensorRecord(hardware_name, hardware_type, sensor_name, sensor_type, value))
            except Exception:
                continue
        try:
            for child in list(getattr(hardware, "SubHardware", [])):
                records.extend(self._collect_hardware_sensors(child))
        except Exception:
            pass
        return records


class CpuService:
    def __init__(self, lhm_adapter: Optional[_LibreHardwareMonitorAdapter] = None) -> None:
        self.lhm_adapter = lhm_adapter or _LibreHardwareMonitorAdapter()

    def collect(self) -> CpuData:
        data = CpuData()
        try:
            info = self._read_wmi_cpu_info()
            data.name = info.get("name") or data.name
            data.manufacturer = info.get("manufacturer") or data.manufacturer
            data.architecture = info.get("architecture") or data.architecture
            data.max_frequency_mhz = info.get("max_frequency_mhz") or data.max_frequency_mhz
            data.physical_cores = info.get("physical_cores") or data.physical_cores
            data.logical_cores = info.get("logical_cores") or data.logical_cores
            data.base_frequency_mhz = info.get("base_frequency_mhz") or data.base_frequency_mhz
            data.current_frequency_mhz = info.get("current_frequency_mhz") or data.current_frequency_mhz
        except Exception:
            pass

        if psutil is not None:
            try:
                if data.physical_cores == "Não disponível":
                    data.physical_cores = str(psutil.cpu_count(logical=False) or "Não disponível")
                if data.logical_cores == "Não disponível":
                    data.logical_cores = str(psutil.cpu_count() or "Não disponível")
            except Exception:
                pass

        lhm_info = self._read_lhm_cpu_info()
        if lhm_info.get("usage_percent"):
            data.usage_percent = lhm_info["usage_percent"]
        if lhm_info.get("temperature_c"):
            data.temperature_c = lhm_info["temperature_c"]
        if lhm_info.get("max_temperature_c"):
            data.max_temperature_c = lhm_info["max_temperature_c"]
        if lhm_info.get("per_core_load"):
            data.per_core_load = lhm_info["per_core_load"]
        if lhm_info.get("per_core_clock_mhz"):
            data.per_core_clock_mhz = lhm_info["per_core_clock_mhz"]
        if lhm_info.get("power_watts"):
            data.power_watts = lhm_info["power_watts"]
        if lhm_info.get("current_frequency_mhz"):
            data.current_frequency_mhz = lhm_info["current_frequency_mhz"]
        if lhm_info.get("max_frequency_mhz"):
            data.max_frequency_mhz = lhm_info["max_frequency_mhz"]
        return data

    def _read_wmi_cpu_info(self) -> Dict[str, str]:
        output = _run_powershell(
            "Get-CimInstance Win32_Processor | Select-Object -First 1 Name,Manufacturer,Architecture,MaxClockSpeed,NumberOfCores,NumberOfLogicalProcessors,CurrentClockSpeed | ConvertTo-Json -Compress"
        )
        if not output:
            return {}
        try:
            import json
            parsed = json.loads(output)
            if not isinstance(parsed, dict):
                return {}
            return {
                "name": _normalize_value(parsed.get("Name"), "Não disponível"),
                "manufacturer": _normalize_value(parsed.get("Manufacturer"), "Não disponível"),
                "architecture": _normalize_value(parsed.get("Architecture"), "Não disponível"),
                "max_frequency_mhz": f"{parsed.get('MaxClockSpeed', 0)} MHz" if parsed.get("MaxClockSpeed") else "Não disponível",
                "physical_cores": _normalize_value(parsed.get("NumberOfCores"), "Não disponível"),
                "logical_cores": _normalize_value(parsed.get("NumberOfLogicalProcessors"), "Não disponível"),
                "current_frequency_mhz": f"{parsed.get('CurrentClockSpeed', 0)} MHz" if parsed.get("CurrentClockSpeed") else "Não disponível",
            }
        except Exception:
            return {}

    def _read_lhm_cpu_info(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        temperatures: List[Tuple[str, float]] = []
        try:
            if not self.lhm_adapter.initialize():
                return result
            for hardware in self.lhm_adapter.iter_hardware():
                try:
                    if str(getattr(hardware.HardwareType, "ToString", lambda: "")()).lower() != "cpu":
                        continue
                    hardware.Update()
                    for sensor in list(getattr(hardware, "Sensors", [])):
                        try:
                            sensor_name = _normalize_value(getattr(sensor, "Name", None), "")
                            sensor_type = str(getattr(sensor.SensorType, "ToString", lambda: "")()).lower()
                            value = getattr(sensor, "Value", None)
                            if value is None:
                                continue
                            if sensor_type == "load":
                                sensor_name_lower = sensor_name.lower()
                                if self._is_aggregate_load_sensor(sensor_name_lower):
                                    result["usage_percent"] = f"{float(value):.1f}%"
                                else:
                                    result.setdefault("per_core_load", []).append(f"{sensor_name}: {float(value):.1f}%")
                            elif sensor_type == "clock":
                                clock_value = float(value)
                                result.setdefault("per_core_clock_mhz", []).append(f"{sensor_name}: {clock_value:.0f} MHz")
                                if "current" in sensor_name.lower() or ("cpu" in sensor_name.lower() and "clock" in sensor_name.lower()):
                                    result["current_frequency_mhz"] = f"{clock_value:.0f} MHz"
                                if "max" in sensor_name.lower() or "maximum" in sensor_name.lower():
                                    result["max_frequency_mhz"] = f"{clock_value:.0f} MHz"
                            elif sensor_type == "temperature":
                                temp_value = float(value)
                                temperatures.append((sensor_name, temp_value))
                            elif sensor_type == "power" and value is not None:
                                result["power_watts"] = f"{float(value):.1f} W"
                        except Exception:
                            continue
                except Exception:
                    continue
            if temperatures:
                package_sensor = next((t for t in temperatures if "package" in t[0].lower()), None)
                if package_sensor:
                    result["temperature_c"] = f"{package_sensor[1]:.1f}°C"
                else:
                    preferred_sensor = self._select_preferred_temperature(temperatures)
                    result["temperature_c"] = f"{preferred_sensor[1]:.1f}°C"
                result["max_temperature_c"] = f"{max(temp[1] for temp in temperatures):.1f}°C"
        except Exception:
            return {}
        return result

    @staticmethod
    def _is_aggregate_load_sensor(sensor_name: str) -> bool:
        name = (sensor_name or "").lower()
        if not name:
            return False
        if any(token in name for token in ("core", "thread", "logical", "per-core")):
            return False
        return any(token in name for token in ("total", "package", "overall", "system")) or ("cpu" in name and ("load" in name or "usage" in name))

    @staticmethod
    def _select_preferred_temperature(candidates: List[Tuple[str, float]]) -> Tuple[str, float]:
        if not candidates:
            return ("Sensor", 0.0)

        def score(item: Tuple[str, float]) -> int:
            name = str(item[0]).lower()
            score_value = 0
            if "package" in name:
                score_value += 5
            if "cpu" in name:
                score_value += 2
            if any(token in name for token in ("core", "thread", "die", "module")):
                score_value -= 3
            return score_value

        return max(candidates, key=score)


class MemoryService:
    def collect(self) -> MemoryData:
        data = MemoryData()
        if psutil is not None:
            try:
                mem = psutil.virtual_memory()
                data.total_capacity_gb = f"{mem.total / (1024 ** 3):.2f} GB"
                data.used_capacity_gb = f"{mem.used / (1024 ** 3):.2f} GB"
                data.free_capacity_gb = f"{mem.available / (1024 ** 3):.2f} GB"
                data.used_percent = f"{mem.percent:.1f}%"
            except Exception:
                pass
        info = self._read_wmi_memory_info()
        data.speed_mhz = info.get("speed_mhz") or data.speed_mhz
        data.type_name = info.get("type_name") or data.type_name
        data.manufacturer = info.get("manufacturer") or data.manufacturer
        data.module_count = info.get("module_count") or data.module_count
        return data

    def _read_wmi_memory_info(self) -> Dict[str, str]:
        output = _run_powershell(
            "Get-CimInstance Win32_PhysicalMemory | Select-Object Speed,Manufacturer,Capacity,MemoryType | ConvertTo-Json -Compress"
        )
        if not output:
            return {}
        try:
            import json
            parsed = json.loads(output)
            if isinstance(parsed, list):
                if not parsed:
                    return {}
                first = parsed[0]
                speed = first.get("Speed")
                memory_type = first.get("MemoryType")
                return {
                    "speed_mhz": f"{speed} MHz" if speed else "Não disponível",
                    "type_name": self._decode_memory_type(memory_type),
                    "manufacturer": _normalize_value(first.get("Manufacturer"), "Não disponível"),
                    "module_count": str(len(parsed)),
                }
            if isinstance(parsed, dict):
                speed = parsed.get("Speed")
                memory_type = parsed.get("MemoryType")
                return {
                    "speed_mhz": f"{speed} MHz" if speed else "Não disponível",
                    "type_name": self._decode_memory_type(memory_type),
                    "manufacturer": _normalize_value(parsed.get("Manufacturer"), "Não disponível"),
                    "module_count": "1",
                }
        except Exception:
            return {}
        return {}

    @staticmethod
    def _decode_memory_type(memory_type: Optional[int]) -> str:
        mapping = {
            20: "DDR",
            21: "DDR2",
            24: "DDR3",
            26: "DDR4",
            28: "DDR5",
        }
        if memory_type in mapping:
            return mapping[memory_type]
        return "Não suportado"


class DiskService:
    def __init__(self, lhm_adapter: Optional[_LibreHardwareMonitorAdapter] = None) -> None:
        self.lhm_adapter = lhm_adapter or _LibreHardwareMonitorAdapter()

    def collect(self) -> List[DiskData]:
        disks: List[DiskData] = []
        storage_info = self._read_lhm_storage_info()
        if psutil is not None:
            try:
                for partition in psutil.disk_partitions(all=False):
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                    except OSError:
                        continue
                    disk = DiskData(
                        name=partition.device or partition.mountpoint or "Não disponível",
                        model=partition.device or "Não disponível",
                        total_capacity_gb=f"{usage.total / (1024 ** 3):.2f} GB",
                        used_capacity_gb=f"{usage.used / (1024 ** 3):.2f} GB",
                        free_capacity_gb=f"{usage.free / (1024 ** 3):.2f} GB",
                        file_system=partition.fstype or "Não disponível",
                        drive_letter=self._get_drive_letter(partition.mountpoint),
                    )
                    matched = self._find_matching_storage_info(storage_info, disk)
                    if matched:
                        disk.temperature_c = matched.get("temperature_c", "Sensor não suportado pelo hardware.")
                        disk.health_percent = matched.get("health_percent", "Sensor não suportado pelo hardware.")
                        disk.remaining_life_percent = matched.get("remaining_life_percent", "Sensor não suportado pelo hardware.")
                        disk.power_on_hours = matched.get("power_on_hours", "Sensor não suportado pelo hardware.")
                        disk.disk_type = matched.get("disk_type", disk.disk_type)
                        disk.manufacturer = matched.get("manufacturer", disk.manufacturer)
                        disk.model = matched.get("model", disk.model)
                        disk.serial_number = matched.get("serial_number", disk.serial_number)
                    disks.append(disk)
            except Exception:
                pass
        if not disks:
            return [DiskData()]
        return disks

    def _find_matching_storage_info(self, storage_info: List[Dict[str, str]], disk: DiskData) -> Optional[Dict[str, str]]:
        name_lower = disk.name.lower()
        for info in storage_info:
            if info.get("model") and info["model"].lower() in name_lower:
                return info
            if info.get("name") and info["name"].lower() in name_lower:
                return info
        return storage_info[0] if storage_info else None

    def _read_lhm_storage_info(self) -> List[Dict[str, str]]:
        storage_records: List[Dict[str, str]] = []
        if not self.lhm_adapter.initialize():
            return storage_records
        self.lhm_adapter.update_all_hardware()
        for hardware in self.lhm_adapter.iter_hardware():
            try:
                hw_type = str(getattr(getattr(hardware, "HardwareType", None), "ToString", lambda: "")()).lower()
                if "storage" not in hw_type and "controller" not in hw_type and "ssd" not in hw_type and "hdd" not in hw_type:
                    continue
                record = {
                    "name": _normalize_value(getattr(hardware, "Name", None), "Não disponível"),
                    "model": _normalize_value(getattr(hardware, "Name", None), "Não disponível"),
                    "manufacturer": "Não disponível",
                    "serial_number": "Não disponível",
                    "disk_type": _normalize_value(hw_type, "Não disponível"),
                    "temperature_c": "Sensor não suportado pelo hardware.",
                    "health_percent": "Sensor não suportado pelo hardware.",
                    "remaining_life_percent": "Sensor não suportado pelo hardware.",
                    "power_on_hours": "Sensor não suportado pelo hardware.",
                }
                for sensor in list(getattr(hardware, "Sensors", [])):
                    try:
                        sensor_name = _normalize_value(getattr(sensor, "Name", None), "Desconhecido").lower()
                        sensor_type = str(getattr(getattr(sensor, "SensorType", None), "ToString", lambda: "")()).lower()
                        value_raw = getattr(sensor, "Value", None)
                        if value_raw is None:
                            continue
                        value = f"{float(value_raw):.1f}"
                        if sensor_type == "temperature":
                            record["temperature_c"] = f"{value}°C"
                        elif sensor_type == "level":
                            if "remaining life" in sensor_name or "life" in sensor_name:
                                record["remaining_life_percent"] = f"{value}%"
                            elif "health" in sensor_name or "overall health" in sensor_name:
                                record["health_percent"] = f"{value}%"
                            elif "power on hours" in sensor_name or "power on" in sensor_name:
                                record["power_on_hours"] = f"{value}"
                        elif sensor_type == "load" and ("health" in sensor_name or "life" in sensor_name):
                            record["health_percent"] = f"{value}%"
                    except Exception:
                        continue
                storage_records.append(record)
            except Exception:
                continue
        return storage_records

    @staticmethod
    def _get_drive_letter(path: Optional[str]) -> str:
        if not path:
            return "Não disponível"
        root = os.path.splitdrive(path)[0]
        if root:
            return root.rstrip(":")
        return os.path.basename(path) or "Não disponível"


class GpuService:
    def __init__(self, lhm_adapter: Optional[_LibreHardwareMonitorAdapter] = None) -> None:
        self.lhm_adapter = lhm_adapter or _LibreHardwareMonitorAdapter()

    def collect(self) -> GpuData:
        data = GpuData()
        if self.lhm_adapter.initialize():
            try:
                for hardware in self.lhm_adapter.iter_hardware():
                    try:
                        hw_type = str(getattr(getattr(hardware, "HardwareType", None), "ToString", lambda: "")()).lower()
                        if "gpu" not in hw_type and "graphics" not in hw_type:
                            continue
                        hardware.Update()
                        data.name = _normalize_value(getattr(hardware, "Name", None), data.name)
                        for sensor in list(getattr(hardware, "Sensors", [])):
                            try:
                                sensor_name = _normalize_value(getattr(sensor, "Name", None), "").lower()
                                sensor_type = str(getattr(getattr(sensor, "SensorType", None), "ToString", lambda: "")()).lower()
                                value = getattr(sensor, "Value", None)
                                if value is None:
                                    continue
                                if sensor_type == "load" and ("gpu" in sensor_name or "total" in sensor_name):
                                    data.usage_percent = f"{float(value):.1f}%"
                                elif sensor_type == "temperature":
                                    data.temperature_c = f"{float(value):.1f}°C"
                                elif sensor_type == "clock":
                                    data.clock_mhz = f"{float(value):.0f} MHz"
                                elif sensor_type == "data" and "memory" in sensor_name:
                                    data.dedicated_memory_gb = f"{float(value) / 1024:.2f} GB"
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                pass
        return data


class MotherboardService:
    def collect(self) -> MotherboardData:
        data = MotherboardData()
        try:
            base_output = _run_powershell(
                "Get-CimInstance Win32_BaseBoard | Select-Object -First 1 Manufacturer,Product | ConvertTo-Json -Compress"
            )
            if base_output:
                import json
                parsed = json.loads(base_output)
                if isinstance(parsed, dict):
                    data.manufacturer = _normalize_value(parsed.get("Manufacturer"), "Não disponível")
                    data.model = _normalize_value(parsed.get("Product"), "Não disponível")
        except Exception:
            pass
        try:
            bios_output = _run_powershell(
                "Get-CimInstance Win32_BIOS | Select-Object -First 1 SMBIOSBIOSVersion,ReleaseDate | ConvertTo-Json -Compress"
            )
            if bios_output:
                import json
                parsed = json.loads(bios_output)
                if isinstance(parsed, dict):
                    data.bios_version = _normalize_value(parsed.get("SMBIOSBIOSVersion"), "Não disponível")
                    data.bios_date = _normalize_value(parsed.get("ReleaseDate"), "Não disponível")
        except Exception:
            pass
        return data


class SystemService:
    def collect(self) -> SystemData:
        data = SystemData()
        data.os_name = platform.system() or "Não disponível"
        data.computer_name = platform.node() or "Não disponível"
        data.version = platform.version() or "Não disponível"
        data.build = platform.release() or "Não disponível"
        data.architecture = platform.machine() or "Não disponível"
        if psutil is not None:
            try:
                uptime_seconds = time.time() - psutil.boot_time()
                data.uptime = self._format_uptime(uptime_seconds)
            except Exception:
                data.uptime = "Não disponível"
        else:
            data.uptime = "Não disponível"
        return data

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        delta = timedelta(seconds=int(seconds))
        parts = []
        if delta.days:
            parts.append(f"{delta.days} dia(s)")
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            parts.append(f"{hours} hora(s)")
        if minutes:
            parts.append(f"{minutes} minuto(s)")
        return ", ".join(parts) or "menos de 1 minuto"


class HardwareService:
    def __init__(self) -> None:
        self.lhm_adapter = _LibreHardwareMonitorAdapter()
        self.cpu_service = CpuService(self.lhm_adapter)
        self.memory_service = MemoryService()
        self.disk_service = DiskService(self.lhm_adapter)
        self.gpu_service = GpuService(self.lhm_adapter)
        self.motherboard_service = MotherboardService()
        self.system_service = SystemService()

    def collect(self) -> ComputerHardwareData:
        self.lhm_adapter.initialize()
        self.lhm_adapter.update_all_hardware()
        data = ComputerHardwareData()
        data.cpu = self.cpu_service.collect()
        data.memory = self.memory_service.collect()
        data.disks = self.disk_service.collect()
        data.gpu = self.gpu_service.collect()
        data.motherboard = self.motherboard_service.collect()
        data.system = self.system_service.collect()
        data.sensor_records = self.lhm_adapter.get_all_sensor_records()
        data.collected_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return data


def _run_powershell(command: str) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""
