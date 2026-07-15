import json
import subprocess
import time
import unittest
from unittest import mock

from modules.collector_service import HardwareCollectorService
from modules.hardware_service import HardwareService


class CollectorServiceTest(unittest.TestCase):
    def test_collect_reuses_cached_result_within_ttl(self):
        calls = 0

        def fake_collector():
            nonlocal calls
            calls += 1
            return {"cpu": {"name": "CPU Test"}}

        service = HardwareCollectorService(collector=fake_collector, ttl_seconds=10.0)

        first = service.collect()
        second = service.collect()

        self.assertEqual(first, second)
        self.assertEqual(calls, 1)

    def test_collect_refreshes_when_forced(self):
        calls = 0

        def fake_collector():
            nonlocal calls
            calls += 1
            return {"cpu": {"name": f"CPU {calls}"}}

        service = HardwareCollectorService(collector=fake_collector, ttl_seconds=10.0)

        first = service.collect()
        refreshed = service.collect(force=True)

        self.assertEqual(first["cpu"]["name"], "CPU 1")
        self.assertEqual(refreshed["cpu"]["name"], "CPU 2")
        self.assertEqual(calls, 2)

    def test_try_load_via_dotnet_host_returns_empty_payload_when_dotnet_is_missing(self):
        service = HardwareService()

        with mock.patch.object(service, "_detect_dotnet_executable", return_value=None):
            payload = service._try_load_via_dotnet_host()

        self.assertEqual(payload, {})

    def test_try_load_via_dotnet_host_uses_subprocess_when_available(self):
        service = HardwareService()
        payload = {"cpu": {"name": "CPU Test"}, "memory": {"total": "8 GB"}}

        def fake_run(*args, **kwargs):
            self.assertEqual(args[0][0], "dotnet")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=json.dumps(payload), stderr="")

        with mock.patch.object(service, "_detect_dotnet_executable", return_value="dotnet"), mock.patch("modules.hardware_service.subprocess.run", side_effect=fake_run):
            result = service._try_load_via_dotnet_host()

        self.assertEqual(result, payload)


if __name__ == "__main__":
    unittest.main()
