import os
import shutil
import tempfile
from typing import List


class CleanupManager:
    def __init__(self):
        self.temp_dirs = [
            os.path.join(os.environ.get("TEMP", tempfile.gettempdir())),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Temp"),
        ]

    def run_cleanup(self) -> List[str]:
        results = []
        for path in self.temp_dirs:
            if not path or not os.path.isdir(path):
                continue
            removed = 0
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                try:
                    if os.path.isfile(full_path) or os.path.islink(full_path):
                        os.unlink(full_path)
                    elif os.path.isdir(full_path):
                        shutil.rmtree(full_path, ignore_errors=True)
                    removed += 1
                except Exception:
                    continue
            results.append(f"{path}: {removed} itens processados")
        if not results:
            results.append("Nenhuma pasta temporária válida encontrada.")
        return results
