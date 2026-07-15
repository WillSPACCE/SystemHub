import os
import platform
import re
import shutil
import socket
import subprocess
from typing import Dict

try:
    import psutil
except ImportError:  # pragma: no cover - fallback for editable environments
    psutil = None

# Tentativa de usar LibreHardwareMonitor via pythonnet (Windows/.NET)
try:
    import clr
    _lhm_available = False
    _computer = None

    def _init_lhm():
        global _lhm_available, _computer
        if _lhm_available:
            return
        # caminhos possíveis para a DLL. O usuário deve colocar LibreHardwareMonitorLib.dll
        # ao lado do projeto ou em modules/ se quiser usar as funções nativamente.
        dll_candidates = [
            os.path.join(os.path.dirname(__file__), "LibreHardwareMonitorLib.dll"),
            os.path.join(os.getcwd(), "LibreHardwareMonitorLib.dll"),
        ]
        for dll in dll_candidates:
            try:
                if os.path.exists(dll):
                    clr.AddReference(dll)
                    from LibreHardwareMonitor import Hardware as _LH
                    from LibreHardwareMonitor.Hardware import Computer as _Computer
                    _computer = _Computer()
                    _computer.IsCpuEnabled = True
                    _computer.IsMotherboardEnabled = True
                    _computer.IsGpuEnabled = True
                    _computer.Open()
                    _lhm_available = True
                    return
            except Exception:
                continue
except Exception:
    clr = None
    _lhm_available = False
    _computer = None


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


def _get_cpu_temperature() -> str:
    # Prioriza LibreHardwareMonitor quando disponível
    try:
        if _computer is not None or (clr is not None and not _lhm_available):
            _init_lhm()
        if _lhm_available and _computer is not None:
            for hw in _computer.Hardware:
                try:
                    if hw.HardwareType.ToString().lower() == "cpu":
                        hw.Update()
                        temperature_candidates = []
                        for sensor in hw.Sensors:
                            try:
                                if sensor.SensorType.ToString().lower() == "temperature" and sensor.Value is not None:
                                    name = str(sensor.Name or "").lower()
                                    if not any(token in name for token in ("core", "thread", "die", "module")):
                                        temperature_candidates.append((sensor.Name, float(sensor.Value)))
                            except Exception:
                                continue
                        if temperature_candidates:
                            preferred = max(
                                temperature_candidates,
                                key=lambda item: ("package" in str(item[0]).lower()) * 5 + ("cpu" in str(item[0]).lower()) * 2),
                            )
                            return f"{preferred[1]:.1f}°C"
                except Exception:
                    continue
    except Exception:
        pass

    # Fallbacks: psutil e PowerShell
    if psutil is not None:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                preferred_keys = ("coretemp", "cpu_thermal", "k10temp", "cpu", "cpu-package")
                for key in preferred_keys:
                    if key in temps and temps[key]:
                        return f"{temps[key][0].current}°C"

                for values in temps.values():
                    if values:
                        return f"{values[0].current}°C"
        except Exception:
            pass

    output = _run_powershell(
        "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object -First 1 -ExpandProperty CurrentTemperature"
    )
    if output:
        try:
            temp = float(output) / 10 - 273.15
            return f"{temp:.1f}°C"
        except ValueError:
            return "N/A"

    return "N/A"


def _get_cpu_usage() -> str:
    """Retorna uso de CPU usando LibreHardwareMonitor quando possível, senão psutil."""
    try:
        if _computer is not None or (clr is not None and not _lhm_available):
            _init_lhm()
        if _lhm_available and _computer is not None:
            for hw in _computer.Hardware:
                try:
                    if hw.HardwareType.ToString().lower() == "cpu":
                        hw.Update()
                        for sensor in hw.Sensors:
                            try:
                                if sensor.SensorType.ToString().lower() == "load" and sensor.Value is not None:
                                    name = sensor.Name.lower() if sensor.Name else ""
                                    if any(token in name for token in ("core", "thread", "logical")):
                                        continue
                                    if any(token in name for token in ("total", "package", "overall", "system")) or ("cpu" in name and ("load" in name or "usage" in name)):
                                        return f"{float(sensor.Value):.0f}%"
                            except Exception:
                                continue
                except Exception:
                    continue
    except Exception:
        pass

    if psutil is not None:
        try:
            return f"{psutil.cpu_percent(interval=None)}%"
        except Exception:
            pass

    return "N/A"


def _ensure_smartctl() -> str:
    candidates = [
        shutil.which("smartctl"),
        r"C:\Program Files\smartmontools\bin\smartctl.exe",
        r"C:\Program Files (x86)\smartmontools\bin\smartctl.exe",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    if shutil.which("winget"):
        subprocess.run(
            ["winget", "install", "--id", "smartmontools.smartmontools", "-e", "--source", "winget"],
            capture_output=True,
            text=True,
            check=False,
        )
        for candidate in candidates[1:]:
            if candidate and os.path.exists(candidate):
                return candidate

    return ""


def _get_ssd_info() -> Dict[str, str]:
    data: Dict[str, str] = {
        "SSD saúde": "N/A",
        "SSD temperatura": "N/A",
        "SSD dispositivo": "N/A",
    }

    health_output = _run_powershell(
        "Get-PhysicalDisk | Select-Object FriendlyName,HealthStatus,DeviceId | ConvertTo-Json -Compress"
    )
    if health_output:
        try:
            import json

            disks = json.loads(health_output)
            if isinstance(disks, list) and disks:
                first_disk = disks[0]
                data["SSD saúde"] = first_disk.get("HealthStatus", "N/A")
                data["SSD dispositivo"] = first_disk.get("FriendlyName", "N/A")
        except Exception:
            pass

    smartctl = _ensure_smartctl()
    if not smartctl:
        return data

    candidates = ["/dev/sda", "/dev/sdb", "/dev/nvme0n1", "\\\\.\\PhysicalDrive0", "\\\\.\\PhysicalDrive1"]
    if smartctl:
        try:
            result = subprocess.run([smartctl, "--scan"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    device = line.split()[0].strip()
                    if device and device.startswith("/dev/"):
                        candidates.insert(0, device)
                        break
        except Exception:
            pass

    for device in candidates:
        if not device:
            continue
        try:
            commands = [[smartctl, "-a", device]]
            if device.startswith("/dev/"):
                commands = [[smartctl, "-d", "nvme", "-a", device], [smartctl, "-a", device]]
            elif device.startswith("\\\\"):
                commands = [[smartctl, "-a", device]]

            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    output = result.stdout
                    for line in output.splitlines():
                        if "SMART overall-health self-assessment test result" in line:
                            data["SSD saúde"] = line.split(":", 1)[-1].strip() or data["SSD saúde"]
                        temperature_match = re.search(r"Temperature[:\s]+(\d+)", line)
                        if temperature_match:
                            data["SSD temperatura"] = f"{temperature_match.group(1)}°C"
                        elif "Temperature_Celsius" in line:
                            temp_value = line.split()[-1]
                            try:
                                data["SSD temperatura"] = f"{float(temp_value)}°C"
                            except ValueError:
                                continue
                    if data["SSD saúde"] != "N/A" or data["SSD temperatura"] != "N/A":
                        data["SSD dispositivo"] = device
                        return data
                    break
        except Exception:
            continue

    if data["SSD saúde"] == "N/A":
        data["SSD saúde"] = "OK"

    return data


def collect_system_info() -> Dict[str, str]:
    info: Dict[str, str] = {}
    info["Sistema operacional"] = platform.system() + " " + platform.release()
    info["Versão"] = platform.version()
    info["Arquitetura"] = platform.machine()
    info["Nome do computador"] = platform.node()
    info["Usuário"] = os.getlogin() if hasattr(os, "getlogin") else "N/A"

    if psutil is not None:
        info["CPU"] = f"{psutil.cpu_freq().current:.0f} MHz" if psutil.cpu_freq() else "N/A"
        info["CPU (modelo)"] = platform.processor() or "N/A"
        mem = psutil.virtual_memory()
        info["RAM total"] = f"{mem.total / (1024 ** 3):.1f} GB"
        info["RAM disponível"] = f"{mem.available / (1024 ** 3):.1f} GB"
        info["Uso de CPU"] = _get_cpu_usage()

        disks = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append(f"{partition.device} -> {usage.total / (1024 ** 3):.1f} GB")
            except OSError:
                continue
        info["Discos"] = "; ".join(disks) if disks else "N/A"
    else:
        info["CPU"] = "N/A"
        info["RAM total"] = "N/A"
        info["RAM disponível"] = "N/A"
        info["Discos"] = "N/A"

    info["Temperatura CPU"] = _get_cpu_temperature()
    info.update(_get_ssd_info())
    info["IP local"] = socket.gethostbyname(socket.gethostname())
    return info
