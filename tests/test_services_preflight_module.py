from __future__ import annotations

import tempfile
import sys
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import services_preflight


class TestServicesPreflight(unittest.TestCase):
    def test_http_get_reads_status_and_body(self) -> None:
        class _Resp:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b"{}"

        with patch.object(services_preflight.urllib.request, "urlopen", return_value=_Resp()):
            status, body = services_preflight._http_get("http://x/health", timeout_sec=0.01)
        self.assertEqual(status, 204)
        self.assertEqual(body, b"{}")

    def test_check_url_json_ok(self) -> None:
        with patch.object(services_preflight, "_http_get", return_value=(200, b"{}")):
            r = services_preflight.check_url_json("http://x/health", timeout_sec=0.01)
        self.assertTrue(r.ok)
        self.assertEqual(r.error, "")

    def test_check_url_json_http_status(self) -> None:
        with patch.object(services_preflight, "_http_get", return_value=(500, b"{}")):
            r = services_preflight.check_url_json("http://x/health", timeout_sec=0.01)
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "http_status")
        self.assertEqual(r.status, 500)

    def test_check_url_json_invalid_json(self) -> None:
        with patch.object(services_preflight, "_http_get", return_value=(200, b"nope")):
            r = services_preflight.check_url_json("http://x/health", timeout_sec=0.01)
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "invalid_json")

    def test_check_url_json_http_error(self) -> None:
        err = urllib.error.HTTPError(url="http://x/health", code=404, msg="no", hdrs=Message(), fp=None)
        try:
            with patch.object(services_preflight, "_http_get", side_effect=err):
                r = services_preflight.check_url_json("http://x/health", timeout_sec=0.01)
            self.assertFalse(r.ok)
            self.assertEqual(r.error, "http_error")
            self.assertEqual(r.status, 404)
        finally:
            try:
                err.close()
            except Exception:
                pass

    def test_wait_ready_stops_on_success(self) -> None:
        checks = [
            services_preflight.ServiceCheck(name="", url="u", ok=False, status=0, error="x"),
            services_preflight.ServiceCheck(name="", url="u", ok=True, status=200, error=""),
        ]
        with (
            patch.object(services_preflight, "check_url_json", side_effect=checks),
            patch.object(services_preflight.time, "sleep", return_value=None),
        ):
            r = services_preflight.wait_ready("u", timeout_sec=0.01, attempts=10, sleep_sec=999)
        self.assertTrue(r.ok)
        self.assertEqual(r.status, 200)

    def test_wait_ready_returns_last_failure(self) -> None:
        checks = [
            services_preflight.ServiceCheck(name="", url="u", ok=False, status=500, error="x"),
            services_preflight.ServiceCheck(name="", url="u", ok=False, status=503, error="y"),
        ]
        with (
            patch.object(services_preflight, "check_url_json", side_effect=checks),
            patch.object(services_preflight.time, "sleep", return_value=None),
        ):
            r = services_preflight.wait_ready("u", timeout_sec=0.01, attempts=2, sleep_sec=0.0)
        self.assertFalse(r.ok)
        self.assertEqual(r.status, 503)

    def test_url_builders_and_default_lm_url(self) -> None:
        self.assertEqual(services_preflight.rag_health_url("http://127.0.0.1:8011"), "http://127.0.0.1:8011/health")
        self.assertEqual(services_preflight.lm_models_url("http://127.0.0.1:1234"), "http://127.0.0.1:1234/v1/models")
        with patch.dict(services_preflight.os.environ, {}, clear=True):
            self.assertEqual(services_preflight.default_lm_studio_base_url(), "http://127.0.0.1:1234")
        with patch.dict(services_preflight.os.environ, {"LMSTUDIO_BASE_URL": "http://x:1"}, clear=True):
            self.assertEqual(services_preflight.default_lm_studio_base_url(), "http://x:1")

    def test_find_lm_studio_exe_first_existing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            local = root / "Local"
            pf = root / "PF"
            pfx86 = root / "PF86"
            exe = local / "Programs" / "LM Studio" / "LM Studio.exe"
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.write_text("", encoding="utf-8")
            with patch.dict(
                services_preflight.os.environ,
                {"LOCALAPPDATA": str(local), "PROGRAMFILES": str(pf), "PROGRAMFILES(X86)": str(pfx86)},
                clear=True,
            ):
                got = services_preflight.find_lm_studio_exe()
        self.assertEqual(got, exe)

    def test_try_start_lm_studio_exe_missing(self) -> None:
        with patch.object(services_preflight, "find_lm_studio_exe", return_value=None):
            ok, err = services_preflight.try_start_lm_studio()
        self.assertFalse(ok)
        self.assertEqual(err, "lm_studio_exe_missing")

    def test_try_start_lm_studio_popen_exception(self) -> None:
        fake_exe = Path("C:/tmp/LM Studio.exe")
        with (
            patch.object(services_preflight, "find_lm_studio_exe", return_value=fake_exe),
            patch.object(services_preflight.subprocess, "Popen", side_effect=RuntimeError("boom")),
        ):
            ok, err = services_preflight.try_start_lm_studio()
        self.assertFalse(ok)
        self.assertIn("boom", err)

    def test_try_start_rag_missing_script(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ok, err = services_preflight.try_start_rag("python", Path(td), base_url="http://127.0.0.1:8011")
        self.assertFalse(ok)
        self.assertIn("rag_server_missing:", err)

    def test_try_start_rag_sets_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            (cwd / "rag_server.py").write_text("print('ok')\n", encoding="utf-8")

            captured_env: dict[str, str] = {}

            def fake_popen(argv: list[str], cwd: str, stdout, stderr, env: dict[str, str]):
                captured_env.update(dict(env))
                return object()

            with (
                patch.object(services_preflight.subprocess, "Popen", side_effect=fake_popen),
                patch.object(services_preflight.time, "strftime", return_value="20260222-000000"),
            ):
                ok, err = services_preflight.try_start_rag(
                    sys.executable,
                    cwd,
                    base_url="http://127.0.0.1:8011",
                )

            self.assertTrue(ok)
            self.assertEqual(err, "")
            self.assertEqual(captured_env.get("RAG_HOST"), "127.0.0.1")
            self.assertEqual(captured_env.get("RAG_PORT"), "8011")
            self.assertEqual(captured_env.get("RAG_BASE_URL"), "http://127.0.0.1:8011")

    def test_try_start_rag_popen_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            (cwd / "rag_server.py").write_text("print('ok')\n", encoding="utf-8")
            with patch.object(services_preflight.subprocess, "Popen", side_effect=RuntimeError("spawn failed")):
                ok, err = services_preflight.try_start_rag(sys.executable, cwd, base_url="http://127.0.0.1:8011")
        self.assertFalse(ok)
        self.assertIn("spawn failed", err)
