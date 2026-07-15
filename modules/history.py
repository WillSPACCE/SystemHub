import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class HistoryManager:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "maintenance_history.json"))

    def load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.storage_path):
            return []
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
                if isinstance(payload, list):
                    return payload
        except Exception:
            return []
        return []

    def append(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        history = self.load()
        history.append({**record, "timestamp": record.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=2, ensure_ascii=False)
        return history

    def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        history = self.load()
        return history[-limit:] if limit else history
