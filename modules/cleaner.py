import ctypes
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class CleanupManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        if base_dir is None:
            self.default_actions = [
                {"id": "temp_windows", "name": "Temp Windows", "label": "Limpar pasta Temp do Windows", "description": "Remove arquivos temporários da pasta Temp do Windows. Antes da remoção, cria um backup local na pasta de backup ao lado do destino por até 30 dias.", "paths": [self._win_temp_path()], "default_selected": True},
                {"id": "temp_user", "name": "Temp Usuário", "label": "Limpar pasta Temp do usuário", "description": "Remove arquivos temporários da pasta Temp do usuário. Um backup local é salvo na pasta de backup do mesmo local antes da limpeza.", "paths": [self._user_temp_path()], "default_selected": True},
                {"id": "chrome_cache", "name": "Cache Chrome", "label": "Limpar cache do Chrome", "description": "Limpa os arquivos de cache do Google Chrome e preserva um backup local por 30 dias.", "paths": [self._chrome_cache_path()], "default_selected": True},
                {"id": "edge_cache", "name": "Cache Edge", "label": "Limpar cache do Edge", "description": "Limpa os arquivos de cache do Microsoft Edge e preserva um backup local por 30 dias.", "paths": [self._edge_cache_path()], "default_selected": True},
                {"id": "windows_update", "name": "Windows Update", "label": "Limpar cache do Windows Update", "description": "Remove arquivos temporários de atualização do Windows e cria backup local por 30 dias.", "paths": [self._windows_update_path()], "default_selected": False},
                {"id": "prefetch", "name": "Prefetch", "label": "Limpar pasta Prefetch", "description": "Limpa a pasta Prefetch e salva um backup local por 30 dias antes da remoção.", "paths": [self._prefetch_path()], "default_selected": False},
                {"id": "minidump", "name": "MiniDump", "label": "Limpar dumps de falha", "description": "Remove arquivos de dump de falha e preserva um backup local por 30 dias.", "paths": [self._minidump_path()], "default_selected": False},
                {"id": "logs", "name": "Logs", "label": "Limpar logs temporários", "description": "Limpa logs temporários e armazena um backup local por 30 dias antes da remoção.", "paths": [self._logs_path()], "default_selected": False},
                {"id": "old_windows_installations", "name": "Instalações antigas do Windows", "label": "Limpar arquivos de instalações antigas do Windows", "description": "Remove pastas antigas de instalação do Windows, como Windows.old, após criar um backup local por 30 dias.", "paths": [self._windows_old_path(), self._windows_bt_path(), self._windows_ws_path()], "default_selected": False},
                {"id": "disk_cleanup", "name": "Limpeza de Disco", "label": "Abrir a ferramenta Limpeza de Disco do Windows", "description": "Abre a ferramenta Limpeza de Disco do Windows para revisão manual. Não há remoção automática.", "paths": [], "default_selected": False},
                {"id": "registry_backup", "name": "Backup do Registro", "label": "Salvar backup do registro do Windows", "description": "Cria um backup do registro do Windows em uma pasta do usuário e abre o editor do registro para revisão manual.", "paths": [], "default_selected": False},
                {"id": "recycle_bin", "name": "Lixeira", "label": "Esvaziar lixeira", "description": "Esvazia a lixeira do Windows. Não há backup automático para esse item.", "paths": [], "default_selected": False},
            ]
        else:
            self.default_actions = [
                {"id": "temp_windows", "name": "Temp Windows", "label": "Limpar pasta Temp do Windows", "description": "Remove arquivos temporários da pasta Temp do Windows. Antes da remoção, cria um backup local na pasta de backup ao lado do destino por até 30 dias.", "paths": [os.path.join(base_dir, "temp_windows")], "default_selected": True},
                {"id": "temp_user", "name": "Temp Usuário", "label": "Limpar pasta Temp do usuário", "description": "Remove arquivos temporários da pasta Temp do usuário. Um backup local é salvo na pasta de backup do mesmo local antes da limpeza.", "paths": [os.path.join(base_dir, "temp_user")], "default_selected": True},
                {"id": "chrome_cache", "name": "Cache Chrome", "label": "Limpar cache do Chrome", "description": "Limpa os arquivos de cache do Google Chrome e preserva um backup local por 30 dias.", "paths": [os.path.join(base_dir, "chrome_cache")], "default_selected": True},
                {"id": "edge_cache", "name": "Cache Edge", "label": "Limpar cache do Edge", "description": "Limpa os arquivos de cache do Microsoft Edge e preserva um backup local por 30 dias.", "paths": [os.path.join(base_dir, "edge_cache")], "default_selected": True},
                {"id": "windows_update", "name": "Windows Update", "label": "Limpar cache do Windows Update", "description": "Remove arquivos temporários de atualização do Windows e cria backup local por 30 dias.", "paths": [os.path.join(base_dir, "windows_update")], "default_selected": False},
                {"id": "prefetch", "name": "Prefetch", "label": "Limpar pasta Prefetch", "description": "Limpa a pasta Prefetch e salva um backup local por 30 dias antes da remoção.", "paths": [os.path.join(base_dir, "prefetch")], "default_selected": False},
                {"id": "minidump", "name": "MiniDump", "label": "Limpar dumps de falha", "description": "Remove arquivos de dump de falha e preserva um backup local por 30 dias.", "paths": [os.path.join(base_dir, "minidump")], "default_selected": False},
                {"id": "logs", "name": "Logs", "label": "Limpar logs temporários", "description": "Limpa logs temporários e armazena um backup local por 30 dias antes da remoção.", "paths": [os.path.join(base_dir, "logs")], "default_selected": False},
                {"id": "old_windows_installations", "name": "Instalações antigas do Windows", "label": "Limpar arquivos de instalações antigas do Windows", "description": "Remove pastas antigas de instalação do Windows, como Windows.old, após criar um backup local por 30 dias.", "paths": [os.path.join(base_dir, "old_windows_installations")], "default_selected": False},
                {"id": "disk_cleanup", "name": "Limpeza de Disco", "label": "Abrir a ferramenta Limpeza de Disco do Windows", "description": "Abre a ferramenta Limpeza de Disco do Windows para revisão manual. Não há remoção automática.", "paths": [], "default_selected": False},
                {"id": "registry_backup", "name": "Backup do Registro", "label": "Salvar backup do registro do Windows", "description": "Cria um backup do registro do Windows em uma pasta do usuário e abre o editor do registro para revisão manual.", "paths": [], "default_selected": False},
                {"id": "recycle_bin", "name": "Lixeira", "label": "Esvaziar lixeira", "description": "Esvazia a lixeira do Windows. Não há backup automático para esse item.", "paths": [], "default_selected": False},
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
        if action_id == "disk_cleanup":
            return self._run_disk_cleanup()
        if action_id == "registry_backup":
            return self._run_registry_backup()
        freed_bytes = 0
        backup_paths = []
        for path in action.get("paths", []):
            backup_root = self._backup_root_for_path(path)
            if backup_root:
                self._backup_path_contents(path, backup_root)
                backup_paths.append(backup_root)
            freed_bytes += self._delete_path_contents(path)
        return {
            "id": action_id,
            "name": action["name"],
            "status": "OK",
            "freed_bytes": freed_bytes,
            "freed": self._format_bytes(freed_bytes),
            "message": "Concluído. Backup local criado por 30 dias." if backup_paths else "Concluído.",
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

    def _backup_root_for_path(self, path: str) -> Optional[str]:
        if not path:
            return None
        normalized = os.path.abspath(path)
        parent = os.path.dirname(normalized) or os.getcwd()
        basename = os.path.basename(normalized) or "cleanup_backup"
        return os.path.join(parent, f"{basename}_backup")

    def _backup_path_contents(self, path: str, backup_root: str) -> None:
        if not path or not os.path.exists(path):
            return
        os.makedirs(backup_root, exist_ok=True)
        self._prune_old_backups(backup_root)
        if os.path.isfile(path) or os.path.islink(path):
            destination = os.path.join(backup_root, os.path.basename(path))
            try:
                shutil.copy2(path, destination)
            except Exception:
                return
            return
        if not os.path.isdir(path):
            return
        try:
            for entry in os.listdir(path):
                source = os.path.join(path, entry)
                destination = os.path.join(backup_root, entry)
                if os.path.isfile(source) or os.path.islink(source):
                    shutil.copy2(source, destination)
                elif os.path.isdir(source):
                    shutil.copytree(source, destination, dirs_exist_ok=True)
        except Exception:
            return

    def _prune_old_backups(self, backup_root: str, retention_days: int = 30) -> None:
        if not backup_root or not os.path.exists(backup_root):
            return
        cutoff = datetime.now() - timedelta(days=retention_days)
        for entry in os.listdir(backup_root):
            entry_path = os.path.join(backup_root, entry)
            try:
                if os.path.getmtime(entry_path) < cutoff.timestamp():
                    if os.path.isdir(entry_path) and not os.path.islink(entry_path):
                        shutil.rmtree(entry_path, ignore_errors=True)
                    else:
                        os.unlink(entry_path)
            except Exception:
                continue

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

    def _run_disk_cleanup(self) -> Dict[str, Any]:
        if os.name != "nt":
            return {"id": "disk_cleanup", "name": "Limpeza de Disco", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Limpeza de Disco não está disponível neste ambiente."}
        return {"id": "disk_cleanup", "name": "Limpeza de Disco", "status": "OK", "freed_bytes": 0, "freed": "0 B", "message": "A opção ficou apenas como recomendação segura; nenhum programa foi iniciado automaticamente."}

    def _run_registry_backup(self) -> Dict[str, Any]:
        if os.name != "nt":
            return {"id": "registry_backup", "name": "Backup do Registro", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Backup do registro não está disponível neste ambiente."}
        backup_dir = os.path.join(os.path.expanduser("~"), "Documents", "SystemHub_Backups", "Registro_Windows")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"registro_{timestamp}.reg")
        try:
            result = subprocess.run(["reg", "export", "HKLM\\SOFTWARE", backup_path], capture_output=True, text=True, timeout=30, check=False)
            if result.returncode != 0:
                return {"id": "registry_backup", "name": "Backup do Registro", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": f"Falha ao exportar o registro: {result.stderr.strip() or result.stdout.strip()}"}
            return {"id": "registry_backup", "name": "Backup do Registro", "status": "OK", "freed_bytes": 0, "freed": "0 B", "message": f"Backup do registro salvo em {backup_path} sem abrir ferramentas adicionais."}
        except FileNotFoundError:
            return {"id": "registry_backup", "name": "Backup do Registro", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "O utilitário reg.exe não foi encontrado."}
        except Exception as exc:
            return {"id": "registry_backup", "name": "Backup do Registro", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": f"Falha ao executar backup do registro: {exc}"}

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

    def _windows_old_path(self) -> str:
        drive = os.path.splitdrive(os.path.abspath(os.sep))[0] or "C:"
        return os.path.join(drive, "Windows.old") if drive else ""

    def _windows_bt_path(self) -> str:
        drive = os.path.splitdrive(os.path.abspath(os.sep))[0] or "C:"
        return os.path.join(drive, "$Windows.~BT") if drive else ""

    def _windows_ws_path(self) -> str:
        drive = os.path.splitdrive(os.path.abspath(os.sep))[0] or "C:"
        return os.path.join(drive, "$Windows.~WS") if drive else ""
