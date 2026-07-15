import os
import platform
import sys
import time
from typing import Any, Dict

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


class SystemService:
    def collect(self) -> Dict[str, Any]:
        info = self._get_wmi_system_info()
        windows_version = self._get_windows_version()
        update_status = self._get_windows_update_status()
        uptime = "Não suportado pelo dispositivo."
        if psutil is not None:
            try:
                uptime = self._format_uptime(psutil.boot_time())
            except Exception:
                pass
        network_name = "Não disponível"
        network_address = ""
        # Try to detect connected network name (SSID for Wi-Fi) on Windows
        try:
            if os.name == "nt":
                import subprocess
                try:
                    out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, stderr=subprocess.DEVNULL)
                    for line in out.splitlines():
                        line = line.strip()
                        if line.lower().startswith("ssid") and ":" in line:
                            # lines like: SSID                   : MyNetwork
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                ssid = parts[1].strip()
                                if ssid and ssid.lower() != "not connected":
                                    network_name = ssid
                                    break
                except Exception:
                    pass

            # Fallback: use psutil to detect first active non-loopback interface and its IPv4
            if psutil is not None:
                try:
                    if_addrs = psutil.net_if_addrs()
                    if_stats = psutil.net_if_stats()
                    for ifname, addrs in if_addrs.items():
                        stats = if_stats.get(ifname)
                        if stats and stats.isup and not ifname.lower().startswith("lo"):
                            # prefer IPv4
                            ip = None
                            for ad in addrs:
                                if getattr(ad, 'family', None) == getattr(psutil, 'AF_INET', 2) or str(getattr(ad, 'family', '')) == 'AddressFamily.AF_INET':
                                    ip = getattr(ad, 'address', None) or getattr(ad, 'addr', '')
                                    break
                            if ip:
                                network_address = ip
                                if network_name == "Não disponível":
                                    network_name = ifname
                                break
                except Exception:
                    pass
        except Exception:
            network_name = "Não disponível"

        return {
            "computer_name": self._safe_text(info.get("computer_name"), os.environ.get("COMPUTERNAME") or platform.node() or "Não disponível"),
            "os_name": self._safe_text(info.get("os_name"), "Windows" if os.name == "nt" else sys.platform or "Não disponível"),
            "version": self._safe_text(windows_version, "Não disponível"),
            "windows_version": self._safe_text(windows_version, "Não disponível"),
            "update_status": self._safe_text(update_status, "Não disponível"),
            "build": self._safe_text(info.get("build"), self._get_windows_build() or "N/A"),
            "architecture": self._safe_text(info.get("architecture"), platform.machine() or "Não disponível"),
            "uptime": uptime,
            "network_name": network_name,
            "network_address": network_address or "Não disponível",
        }

    def _get_wmi_system_info(self) -> Dict[str, Any]:
        return {
            "os_name": "Windows" if os.name == "nt" else sys.platform or "Não disponível",
            "version": self._get_windows_version(),
            "build": self._get_windows_build(),
            "architecture": platform.machine() or "Não disponível",
            "computer_name": os.environ.get("COMPUTERNAME") or platform.node() or "Não disponível",
        }

    def _get_windows_version(self) -> str:
        if os.name == "nt":
            try:
                release, version, _, _ = platform.win32_ver()
                if release and version:
                    return f"Windows {release} ({version})"
                if version:
                    return f"Windows {version}"
            except Exception:
                pass
            try:
                winver = sys.getwindowsversion()
                return f"Windows {winver.major}.{winver.minor} ({winver.build})"
            except Exception:
                pass
        return f"{platform.system()} {platform.release()}" if platform.system() else "Não disponível"

    def _get_windows_build(self) -> str:
        if os.name != "nt":
            return "N/A"
        try:
            winver = sys.getwindowsversion()
            return f"{winver.major}.{winver.minor}.{winver.build}"
        except Exception:
            return "N/A"

    def _get_windows_update_status(self) -> str:
        if os.name != "nt":
            return "Não disponível"
        try:
            import subprocess
            command = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$result = (Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\Results\\Install' -Name LastResult -ErrorAction SilentlyContinue).LastResult; if ($result -eq 0) { 'Atualizações recentes instaladas' } elseif ([string]::IsNullOrWhiteSpace($result)) { 'Sem dados de atualização' } else { 'Atualização com alerta' }",
            ]
            output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)
            status = output.strip()
            if status:
                return status
        except Exception:
            pass
        return "Sem dados de atualização"

    def _format_uptime(self, boot_time: float) -> str:
        seconds = max(0, int(time.time() - boot_time))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        return f"{days} dias, {hours} horas, {minutes} minutos"

    def _safe_text(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text if text else fallback
