import io
import json
import os
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app import run
from contract_schemas import validate_session_close_run
from tests.io_capture import capture_stdio


@contextmanager
def case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_case_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    prev = os.getcwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(prev)
        shutil.rmtree(root, ignore_errors=True)


class SessionCloseWorkflowTests(unittest.TestCase):
    def _assert_session_close_run_contract_v1(self, payload: dict[str, Any]) -> None:
        self.assertEqual(validate_session_close_run(payload), [])

    def test_top_level_session_close_alias_dry_run_contract(self) -> None:
        with case_dir() as root:
            (root / ".trae" / "memory").mkdir(parents=True, exist_ok=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "session", "close", "--dry-run", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue().strip())
            self._assert_session_close_run_contract_v1(payload)
            self.assertTrue(bool(payload.get("dry_run")))
            self.assertEqual(payload.get("status"), "pass")

    def test_workflow_session_close_dry_run_contract(self) -> None:
        with case_dir() as root:
            (root / ".trae" / "memory").mkdir(parents=True, exist_ok=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "session", "close", "--dry-run", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue().strip())
            self._assert_session_close_run_contract_v1(payload)
            self.assertTrue(bool(payload.get("dry_run")))
            self.assertEqual(payload.get("status"), "pass")
            checks = payload.get("checks", {})
            self.assertIsInstance(checks, dict)
            if isinstance(checks, dict):
                self.assertEqual(checks.get("session_close_consistency"), "skipped")

    def test_workflow_session_close_skip_quality_writes_artifacts(self) -> None:
        with case_dir() as root:
            (root / ".trae" / "memory").mkdir(parents=True, exist_ok=True)
            reports = root / "reports"
            reports.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "session",
                        "close",
                        "--skip-quality",
                        "--task-id",
                        "B90",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue().strip())
            self.assertEqual(payload.get("status"), "pass")
            artifacts = payload.get("artifacts", {})
            self.assertIsInstance(artifacts, dict)
            if isinstance(artifacts, dict):
                self.assertTrue(Path(str(artifacts.get("session_close_md", ""))).exists())
                self.assertTrue(Path(str(artifacts.get("session_close_json", ""))).exists())
                self.assertTrue(Path(str(artifacts.get("tracker", ""))).exists())
                self.assertTrue(Path(str(artifacts.get("execution_report", ""))).exists())
            checks = payload.get("checks", {})
            if isinstance(checks, dict):
                self.assertEqual(checks.get("session_close_consistency"), "pass")
                self.assertEqual(checks.get("tracker_report_sync"), "pass")

    def test_workflow_session_close_fails_when_reports_path_is_file(self) -> None:
        with case_dir() as root:
            (root / ".trae" / "memory").mkdir(parents=True, exist_ok=True)
            bad_reports = root / "reports"
            bad_reports.write_text("not a directory", encoding="utf-8")

            with capture_stdio() as (buf, _err):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "session",
                        "close",
                        "--skip-quality",
                        "--reports-dir",
                        str(bad_reports),
                        "--json",
                    ]
                )
            self.assertEqual(code, 1)
            payload = json.loads(buf.getvalue().strip())
            self.assertEqual(payload.get("status"), "fail")
            errors = payload.get("errors", [])
            self.assertIsInstance(errors, list)
            if isinstance(errors, list):
                self.assertGreaterEqual(len(errors), 1)
