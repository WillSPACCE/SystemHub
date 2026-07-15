import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from modules.hardware_service import HardwareService


def _default_hardware_collector() -> Dict[str, Any]:
    service = HardwareService()
    payload = service._try_load_via_dotnet_host()
    if isinstance(payload, dict) and payload:
        payload.setdefault("collected_at", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        return payload

    payload = service._collect_raw_payload()
    if isinstance(payload, dict) and payload:
        payload.setdefault("collected_at", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        return payload
    return {}


class HardwareCollectorService:
    def __init__(self, collector: Optional[Callable[[], Dict[str, Any]]] = None, ttl_seconds: float = 3.0) -> None:
        self._collector = collector or _default_hardware_collector
        self._ttl_seconds = ttl_seconds
        self._cache: Optional[Dict[str, Any]] = None
        self._cached_at: float = 0.0

    def collect(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and self._cache is not None and (now - self._cached_at) < self._ttl_seconds:
            return self._cache

        payload = self._collector()
        if isinstance(payload, dict):
            self._cache = payload
            self._cached_at = now
            return payload
        return {}

    def invalidate(self) -> None:
        self._cache = None
        self._cached_at = 0.0
