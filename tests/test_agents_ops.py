import unittest
from pathlib import Path
from unittest import mock

from agents_ops import _agent_fix_hints, _agent_row_problems, _is_endpoint_up


class AgentsOpsTest(unittest.TestCase):
    def test_is_endpoint_up_rejects_empty_and_invalid(self) -> None:
        self.assertFalse(_is_endpoint_up(""))
        self.assertFalse(_is_endpoint_up("not-a-url"))
        self.assertFalse(_is_endpoint_up("http:///missing-host"))

    def test_is_endpoint_up_true_when_socket_connects(self) -> None:
        class _Conn:
            def __enter__(self) -> object:
                return object()

            def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
                return None

        with mock.patch("agents_ops.socket.create_connection", return_value=_Conn()):
            self.assertTrue(_is_endpoint_up("http://127.0.0.1:8011"))

    def test_gateway_problems_and_fix_hints_deduplicate(self) -> None:
        path = Path("C:/demo/agent_gateway")
        row = {
            "path": str(path),
            "agent_type": "gateway",
            "state": "ok",
            "gateway_base": "",
            "gateway_routes": 0,
            "gateway_up": False,
        }
        problems = _agent_row_problems(row)
        self.assertIn("gateway_base_missing", problems)

        hints = _agent_fix_hints(row)
        expected = f"Get-Content {Path(str(path)).resolve() / 'config' / 'gateway.json'}"
        self.assertEqual(hints, [expected])

    def test_media_storage_problems_and_fix_hints(self) -> None:
        path = Path("C:/demo/media_storage")
        row = {
            "path": str(path),
            "agent_type": "media-storage",
            "state": "ok",
            "media_root": "C:/data/media",
            "media_root_exists": False,
            "work_root": "C:/data/work",
            "work_root_exists": False,
            "publish_root": "",
            "publish_root_exists": False,
        }
        problems = _agent_row_problems(row)
        self.assertIn("media_root_missing", problems)
        self.assertIn("work_root_missing", problems)
        self.assertIn("publish_root_empty", problems)

        hints = _agent_fix_hints(row)
        self.assertIn("Test-Path C:/data/media", hints)
        self.assertIn("New-Item -ItemType Directory -Force -Path C:/data/work", hints)
