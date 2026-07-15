import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import clr
except Exception:  # pragma: no cover
    clr = None

from modules.cpu_service import CpuService
from modules.disk_service import DiskService
from modules.gpu_service import GpuService
from modules.memory_service import MemoryService
from modules.motherboard_service import MotherboardService
from modules.smart_service import SmartService
from modules.system_service import SystemService


class HardwareService:
    def __init__(self) -> None:
        self.cpu_service = CpuService()
        self.memory_service = MemoryService()
        self.disk_service = DiskService()
        self.gpu_service = GpuService()
        self.motherboard_service = MotherboardService()
        self.smart_service = SmartService()
        self.system_service = SystemService()
        self._search_paths: List[str] = []
        self._debug_lines: List[str] = []
        self._dll_path: Optional[str] = None

    def collect(self) -> Dict[str, Any]:
        payload = self._collect_raw_payload()
        system_data = self.system_service.collect()
        cpu_data = self.cpu_service.collect(payload, system_data)
        memory_data = self.memory_service.collect()
        disk_data = self.disk_service.collect(payload)
        disk_data = self.smart_service.collect(disk_data)
        gpu_data = self.gpu_service.collect(payload)
        motherboard_data = self.motherboard_service.collect()

        data: Dict[str, Any] = {
            "cpu": cpu_data,
            "memory": memory_data,
            "disks": disk_data,
            "gpu": gpu_data,
            "motherboard": motherboard_data,
            "system": system_data,
            "sensors": payload.get("sensors", []),
            "debug_file": str(Path(__file__).resolve().parent / "hardware_debug.txt"),
            "log_file": str(Path(__file__).resolve().parent / "hardware_service.log"),
            "dll_path": self._dll_path or "",
            "search_paths": self._search_paths,
            "collected_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
        self._write_debug_file(data)
        self._write_log_file(data)
        return data

    def coletar(self) -> Dict[str, Any]:
        return self.collect()

    def _collect_raw_payload(self) -> Dict[str, Any]:
        self._search_paths = self._build_search_paths()
        payload = self._try_load_via_dotnet_host()
        if payload:
            self._debug_lines.append("Dados coletados via host .NET.")
            return payload

        self._debug_lines.append("Usando dados de fallback do sistema.")
        return {
            "cpu": {},
            "memory": {},
            "disks": [],
            "gpu": {},
            "motherboard": {},
            "system": {},
            "sensors": [],
        }

    def _detect_dotnet_executable(self) -> Optional[str]:
        candidates: List[str] = []
        dotnet_path = shutil.which("dotnet") or shutil.which("dotnet.exe")
        if dotnet_path:
            candidates.append(dotnet_path)
        for path in [
            r"C:\Program Files\dotnet\dotnet.exe",
            r"C:\Program Files (x86)\dotnet\dotnet.exe",
        ]:
            if path and os.path.exists(path):
                candidates.append(path)
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _try_load_via_dotnet_host(self) -> Dict[str, Any]:
        dotnet_path = self._detect_dotnet_executable()
        if not dotnet_path:
            self._debug_lines.append("Host .NET indisponível: dotnet não encontrado.")
            return {}

        root = Path(__file__).resolve().parent
        host_candidates = [
            root / "hardware_host" / "bin" / "Debug" / "net10.0" / "hardware_host.dll",
            root / "hardware_host" / "bin" / "Release" / "net10.0" / "hardware_host.dll",
            root / "hardware_host" / "bin" / "Debug" / "net8.0" / "hardware_host.dll",
            root / "hardware_host" / "bin" / "Release" / "net8.0" / "hardware_host.dll",
        ]
        available_hosts = [str(path) for path in host_candidates if path.exists()]
        if not available_hosts:
            self._debug_lines.append("Host .NET não encontrado nas pastas esperadas.")
            return {}

        self._debug_lines.append(f"Tentando host .NET em {len(available_hosts)} caminho(s).")
        for host_path in available_hosts:
            try:
                completed = subprocess.run(
                    [dotnet_path, host_path],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                self._debug_lines.append(f"Tempo limite atingido ao executar host .NET: {host_path}")
                continue
            except OSError as exc:
                self._debug_lines.append(f"Falha ao invocar host .NET: {exc}")
                continue

            if completed.returncode != 0:
                self._debug_lines.append(f"Host .NET retornou erro {completed.returncode}: {completed.stderr.strip()}")
                continue

            output = (completed.stdout or "").strip()
            if not output:
                self._debug_lines.append("Host .NET não retornou dados.")
                continue

            try:
                parsed = json.loads(output)
                if isinstance(parsed, dict):
                    self._debug_lines.append("Dados coletados via host .NET.")
                    return parsed
            except json.JSONDecodeError as exc:
                self._debug_lines.append(f"Falha ao parsear JSON do host .NET: {exc}")

        self._debug_lines.append("Usando dados de fallback do sistema.")
        return {}

    def _build_search_paths(self) -> List[str]:
        root = Path(__file__).resolve().parent
        candidates = [
            root,
            root / "hardware_host",
            root / "hardware_host" / "bin",
            root / "hardware_host" / "obj",
        ]
        paths = [str(path) for path in candidates if path.exists() and path.is_dir()]
        return sorted(dict.fromkeys(paths))

    def _write_debug_file(self, data: Dict[str, Any]) -> None:
        output_path = Path(__file__).resolve().parent / "hardware_debug.txt"
        lines: List[str] = [
            "====================================",
            "Resumo da coleta",
            "====================================",
            f"Coletado em: {data.get('collected_at', 'Não disponível')}",
            f"DLL: {data.get('dll_path', 'Não encontrada')}",
            "====================================",
            "Sensores:",
        ]
        for record in data.get("sensors", []):
            lines.append(f"Tipo: {record.get('hardware_type', 'Desconhecido')}")
            lines.append(f"Sensor: {record.get('sensor', 'Desconhecido')}")
            lines.append(f"Tipo do Sensor: {record.get('sensor_type', 'Desconhecido')}")
            lines.append(f"Valor: {record.get('value', 'Desconhecido')}")
            lines.append("====================================")
        if not data.get("sensors"):
            lines.append("Nenhum sensor encontrado.")
            lines.append("====================================")
        try:
            output_path.write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            pass

    def _write_log_file(self, data: Dict[str, Any]) -> None:
        output_path = Path(__file__).resolve().parent / "hardware_service.log"
        lines = [
            f"Coletado em: {data.get('collected_at', 'Não disponível')}",
            f"CPU: {data.get('cpu', {}).get('name', 'Não disponível')}",
            f"RAM: {data.get('memory', {}).get('percent', 'Não disponível')}",
            f"Discos: {len(data.get('disks', []))}",
            f"Sistema: {data.get('system', {}).get('os_name', 'Não disponível')}",
        ]
        try:
            output_path.write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            pass


hardware_service = HardwareService()


def coletar() -> Dict[str, Any]:
    return hardware_service.collect()
