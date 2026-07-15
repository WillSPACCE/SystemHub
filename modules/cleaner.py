import ctypes
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional


class CleanupManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        if base_dir is None:
            self.default_actions = [
                {"id": "temp_windows", "name": "Temp Windows", "label": "Limpar pasta Temp do Windows", "paths": [self._win_temp_path()]},
                {"id": "temp_user", "name": "Temp Usuário", "label": "Limpar pasta Temp do usuário", "paths": [self._user_temp_path()]},
                {"id": "chrome_cache", "name": "Cache Chrome", "label": "Limpar cache do Chrome", "paths": [self._chrome_cache_path()]},
                {"id": "edge_cache", "name": "Cache Edge", "label": "Limpar cache do Edge", "paths": [self._edge_cache_path()]},
                {"id": "windows_update", "name": "Windows Update", "label": "Limpar cache do Windows Update", "paths": [self._windows_update_path()]},
                {"id": "prefetch", "name": "Prefetch", "label": "Limpar pasta Prefetch", "paths": [self._prefetch_path()]},
                {"id": "minidump", "name": "MiniDump", "label": "Limpar dumps de falha", "paths": [self._minidump_path()]},
                {"id": "logs", "name": "Logs", "label": "Limpar logs temporários", "paths": [self._logs_path()]},
                {"id": "recycle_bin", "name": "Lixeira", "label": "Esvaziar lixeira", "paths": []},
            ]
        else:
            self.default_actions = [
                {"id": "temp_windows", "name": "Temp Windows", "label": "Limpar pasta Temp do Windows", "paths": [os.path.join(base_dir, "temp_windows")]},
                {"id": "temp_user", "name": "Temp Usuário", "label": "Limpar pasta Temp do usuário", "paths": [os.path.join(base_dir, "temp_user")]},
                {"id": "chrome_cache", "name": "Cache Chrome", "label": "Limpar cache do Chrome", "paths": [os.path.join(base_dir, "chrome_cache")]},
                {"id": "edge_cache", "name": "Cache Edge", "label": "Limpar cache do Edge", "paths": [os.path.join(base_dir, "edge_cache")]},
                {"id": "windows_update", "name": "Windows Update", "label": "Limpar cache do Windows Update", "paths": [os.path.join(base_dir, "windows_update")]},
                {"id": "prefetch", "name": "Prefetch", "label": "Limpar pasta Prefetch", "paths": [os.path.join(base_dir, "prefetch")]},
                {"id": "minidump", "name": "MiniDump", "label": "Limpar dumps de falha", "paths": [os.path.join(base_dir, "minidump")]},
                {"id": "logs", "name": "Logs", "label": "Limpar logs temporários", "paths": [os.path.join(base_dir, "logs")]},
                {"id": "recycle_bin", "name": "Lixeira", "label": "Esvaziar lixeira", "paths": []},
            ]

    def get_default_actions(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self.default_actions]

    def estimate_recovery(self, selected_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        total_bytes = 0
        details: List[Dict[str, Any]] = []
        selected = self._resolve_selected(selected_ids)
        for action in selected:
            size = self._estimate_size_for_action(action)
            total_bytes += size
            details.append({"id": action["id"], "name": action["name"], "bytes": size, "human": self._format_bytes(size)})
        return {"total_bytes": total_bytes, "total_human": self._format_bytes(total_bytes), "details": details}

    def run_cleanup(self, selected_ids: Optional[List[str]] = None, progress_callback: Optional[Any] = None) -> List[Dict[str, Any]]:
        selected = self._resolve_selected(selected_ids)
        results: List[Dict[str, Any]] = []
        for index, action in enumerate(selected, start=1):
            if progress_callback:
                progress_callback(action["name"], "running", f"Executando {action['name']}...", int((index / max(1, len(selected))) * 100))
            result = self._run_action(action)
            results.append(result)
            if progress_callback:
                progress_callback(action["name"], result["status"], result.get("message", ""), int((index / max(1, len(selected))) * 100))
        return results

    def _resolve_selected(self, selected_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
        if not selected_ids:
            return self.get_default_actions()
        selected_map = {item["id"]: item for item in self.default_actions}
        resolved = []
        for item_id in selected_ids:
            action = selected_map.get(item_id)
            if action:
                resolved.append(action)
        return resolved or self.get_default_actions()

    def _run_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_id = action["id"]
        if action_id == "recycle_bin":
            return self._empty_recycle_bin()
        freed_bytes = 0
        for path in action.get("paths", []):
            freed_bytes += self._delete_path_contents(path)
        return {
            "id": action_id,
            "name": action["name"],
            "status": "OK",
            "freed_bytes": freed_bytes,
            "freed": self._format_bytes(freed_bytes),
            "message": "Concluído.",
        }

    def _estimate_size_for_action(self, action: Dict[str, Any]) -> int:
        if action["id"] == "recycle_bin":
            return 0
        total = 0
        for path in action.get("paths", []):
            total += self._calculate_size(path)
        return total

    def _delete_path_contents(self, path: str) -> int:
        if not path or not os.path.exists(path):
            return 0
        total = self._calculate_size(path)
        if os.path.isfile(path) or os.path.islink(path):
            try:
                os.unlink(path)
            except Exception:
                return 0
            return total
        if not os.path.isdir(path):
            return 0
        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isfile(full_path) or os.path.islink(full_path):
                    os.unlink(full_path)
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path, ignore_errors=True)
        except Exception:
            return 0
        return total

    def _calculate_size(self, path: str) -> int:
        if not path or not os.path.exists(path):
            return 0
        if os.path.isfile(path) or os.path.islink(path):
            try:
                return os.path.getsize(path)
            except Exception:
                return 0
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for filename in files:
                    try:
                        total += os.path.getsize(os.path.join(root, filename))
                    except Exception:
                        continue
        except Exception:
            return 0
        return total

    def _empty_recycle_bin(self) -> Dict[str, Any]:
        if os.name != "nt":
            return {"id": "recycle_bin", "name": "Lixeira", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Lixeira não disponível neste ambiente."}
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0)
        except Exception:
            return {"id": "recycle_bin", "name": "Lixeira", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Falha ao esvaziar a lixeira."}
        return {"id": "recycle_bin", "name": "Lixeira", "status": "OK", "freed_bytes": 0, "freed": "0 B", "message": "Lixeira esvaziada."}

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(max(0, value))
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} {units[-1]}"

    def _win_temp_path(self) -> str:
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
        if windir:
            return os.path.join(windir, "Temp")
        return os.path.join(tempfile.gettempdir())

    def _user_temp_path(self) -> str:
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp") if os.environ.get("LOCALAPPDATA") else os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Temp")

    def _chrome_cache_path(self) -> str:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return os.path.join(local_appdata, "Google", "Chrome", "User Data", "Default", "Cache")
        return ""

    def _edge_cache_path(self) -> str:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "Default", "Cache")
        return ""

    def _windows_update_path(self) -> str:
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
        if windir:
            return os.path.join(windir, "SoftwareDistribution", "Download")
        return ""

    def _prefetch_path(self) -> str:
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
        if windir:
            return os.path.join(windir, "Prefetch")
        return ""

    def _minidump_path(self) -> str:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return os.path.join(local_appdata, "CrashDumps")
        return ""

    def _logs_path(self) -> str:
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
        if windir:
            return os.path.join(windir, "Logs")
        return ""
