import io
import json
import os
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock
from uuid import uuid4

from agent_memory_client import HttpResult
from app import run


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


class WorkflowQualityTests(unittest.TestCase):
    def test_quality_summary_json_no_run(self) -> None:
        buf = io.StringIO()
        with mock.patch("cli_quality._run_capture", return_value=(0, "ok", "")):
            with redirect_stdout(buf):
                code = run(["integrator", "quality", "summary", "--json", "--no-run"])
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("kind"), "quality_summary")
        self.assertIn("tools", rows[0])
        self.assertIn("artifacts", rows[0])

    def test_workflow_preflight_memory_report_writes_artifacts(self) -> None:
        with case_dir() as root:
            demo = root / "demo"
            demo.mkdir()
            (demo / "requirements.txt").write_text("x", encoding="utf-8")
            content = root / "note.txt"
            content.write_text("hello", encoding="utf-8")
            reports_dir = root / "reports"

            ok_diag = [
                {"kind": "tool", "name": "python", "path": "python", "status": "ok"},
                {"kind": "tool", "name": "git", "path": "git", "status": "ok"},
            ]
            fake_results = [HttpResult(status=200, body=b"{}", json={"record": {"id": "1"}})]

            buf = io.StringIO()
            with mock.patch("cli_workflow._diagnostics_rows", return_value=ok_diag):
                with mock.patch("cli_workflow.memory_write_file", return_value=fake_results):
                    with redirect_stdout(buf):
                        code = run(
                            [
                                "integrator",
                                "workflow",
                                "preflight-memory-report",
                                "--roots",
                                str(root),
                                "--max-depth",
                                "2",
                                "--reports-dir",
                                str(reports_dir),
                                "--content-file",
                                str(content),
                                "--summary",
                                "s",
                                "--json",
                            ]
                        )

            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            payload = rows[0]
            artifacts = payload.get("artifacts", {})
            self.assertTrue(Path(artifacts["summary_json"]).exists())
            self.assertTrue(Path(artifacts["projects_json"]).exists())
            self.assertTrue(Path(artifacts["errors_log"]).exists())
