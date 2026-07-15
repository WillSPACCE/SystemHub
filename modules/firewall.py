import subprocess
import sys
from typing import List, Dict
import socket
try:
    import psutil
except Exception:
    psutil = None


class FirewallManager:
    def __init__(self):
        self._is_windows = sys.platform.startswith("win")

    def get_state(self) -> bool:
        if not self._is_windows:
            raise OSError("Este recurso é compatível com Windows.")
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return "Estado do firewall" in result.stdout and "Ativado" in result.stdout

    def set_state(self, enabled: bool) -> None:
        if not self._is_windows:
            raise OSError("Este recurso é compatível com Windows.")
        mode = "on" if enabled else "off"
        result = subprocess.run(
            ["netsh", "advfirewall", "set", "allprofiles", "state", mode],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    def allow_port(self, port: int, direction: str = "Entrada") -> None:
        if not self._is_windows:
            raise OSError("Este recurso é compatível com Windows.")
        direction_value = str(direction).strip().lower()
        dir_flag = "out" if direction_value in {"saída", "saida", "out"} else "in"
        # cria regra com nome único por porta para gerenciarmos depois
        name = f"PythonUtilityPort_{port}_TCP_{dir_flag}"
        cmd = [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={name}",
            "protocol=TCP",
            f"localport={port}",
            f"dir={dir_flag}",
            "action=allow",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    def block_port(self, port: int) -> None:
        if not self._is_windows:
            raise OSError("Este recurso é compatível com Windows.")
        name = f"PythonUtilityBlock_{port}_TCP"
        cmd = [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={name}",
            "protocol=TCP",
            f"localport={port}",
            "dir=in",
            "action=block",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    def remove_rule_by_port(self, port: int) -> None:
        if not self._is_windows:
            raise OSError("Este recurso é compatível com Windows.")
        # tenta remover regras criadas pelo utilitário (allow/block) em qualquer direção
        names = [
            f"PythonUtilityPort_{port}_TCP",
            f"PythonUtilityPort_{port}_TCP_in",
            f"PythonUtilityPort_{port}_TCP_out",
            f"PythonUtilityBlock_{port}_TCP",
            f"PythonUtilityBlock_{port}_TCP_in",
            f"PythonUtilityBlock_{port}_TCP_out",
        ]
        for name in names:
            cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"]
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)

    def list_connections(self) -> List[Dict]:
        """Retorna lista de conexões ativas com informações úteis para a UI.

        Cada item: {local_addr, local_port, remote_addr, remote_port, status, pid, process, protocol}
        """
        results = []
        if psutil is not None:
            try:
                for conn in psutil.net_connections(kind='inet'):
                    laddr = conn.laddr if conn.laddr else ()
                    raddr = conn.raddr if conn.raddr else ()
                    proto = 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP' if conn.type == socket.SOCK_DGRAM else 'UNKNOWN'
                    pid = conn.pid or 0
                    proc_name = ''
                    try:
                        if pid:
                            proc = psutil.Process(pid)
                            proc_name = proc.name()
                    except Exception:
                        proc_name = ''
                    item = {
                        'local_addr': laddr.ip if hasattr(laddr, 'ip') else (laddr[0] if len(laddr) > 0 else ''),
                        'local_port': int(laddr.port) if hasattr(laddr, 'port') else (int(laddr[1]) if len(laddr) > 1 else 0),
                        'remote_addr': raddr.ip if hasattr(raddr, 'ip') else (raddr[0] if len(raddr) > 0 else ''),
                        'remote_port': int(raddr.port) if hasattr(raddr, 'port') else (int(raddr[1]) if len(raddr) > 1 else 0),
                        'status': conn.status,
                        'pid': pid,
                        'process': proc_name,
                        'protocol': proto,
                    }
                    results.append(item)
                return results
            except Exception:
                # fallback para netstat
                pass

        # fallback: usar netstat -ano e parse
        try:
            proc = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
            out = proc.stdout.splitlines()
            for line in out:
                line = line.strip()
                if not line or line.startswith('Proto') or line.startswith('Active'):
                    continue
                parts = [p for p in line.split() if p]
                if len(parts) < 4:
                    continue
                proto = parts[0]
                local = parts[1]
                remote = parts[2]
                status = parts[3] if proto.upper().startswith('T') and len(parts) >= 4 else ''
                pid = int(parts[-1]) if parts[-1].isdigit() else 0
                la, lp = (local.rsplit(':', 1) + [''])[:2]
                ra, rp = (remote.rsplit(':', 1) + [''])[:2]
                proc_name = ''
                try:
                    if pid:
                        p = psutil.Process(pid) if psutil is not None else None
                        proc_name = p.name() if p is not None else ''
                except Exception:
                    proc_name = ''
                try:
                    lp = int(lp)
                except Exception:
                    lp = 0
                try:
                    rp = int(rp)
                except Exception:
                    rp = 0
                results.append({
                    'local_addr': la,
                    'local_port': lp,
                    'remote_addr': ra,
                    'remote_port': rp,
                    'status': status,
                    'pid': pid,
                    'process': proc_name,
                    'protocol': 'TCP' if proto.upper().startswith('T') else ('UDP' if proto.upper().startswith('U') else proto),
                })
        except Exception:
            pass

        return results

    def list_rules(self) -> List[Dict]:
        """Lista regras do firewall via netsh e retorna uma lista de dicionários simples.

        Cada item inclui: name, enabled, direction, action, protocol, localport, profile, program
        """
        rules = []
        if not self._is_windows:
            return rules
        try:
            proc = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", "name=all", "verbose"], capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
            out = proc.stdout.splitlines()
            current = {}
            for line in out:
                line = line.rstrip()
                if not line:
                    if current:
                        rules.append(current)
                        current = {}
                    continue
                if ':' not in line:
                    continue
                key, val = line.split(':', 1)
                key = key.strip().lower()
                val = val.strip()
                if key == 'rule name':
                    current['name'] = val
                elif key == 'enabled':
                    current['enabled'] = val
                elif key == 'direction':
                    current['direction'] = val
                elif key == 'action':
                    current['action'] = val
                elif key == 'protocol':
                    current['protocol'] = val
                elif key == 'localport':
                    current['localport'] = val
                elif key == 'profile':
                    current['profile'] = val
                elif key == 'program':
                    current['program'] = val
            if current:
                rules.append(current)
        except Exception:
            pass
        return rules
