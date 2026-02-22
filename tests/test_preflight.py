import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from app import run
from services_preflight import ServiceCheck


class PreflightTests(unittest.TestCase):
    def test_preflight_json_check_only(self) -> None:
        buf = io.StringIO()
        ok = ServiceCheck(name="", url="u", ok=True, status=200, error="")
        with mock.patch("cli.wait_ready", side_effect=[ok, ok]):
            with redirect_stdout(buf):
                code = run(["integrator", "preflight", "--check-only", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload.get("kind"), "preflight")
        self.assertTrue(payload.get("rag", {}).get("ok"))
        self.assertTrue(payload.get("lm_studio", {}).get("ok"))
