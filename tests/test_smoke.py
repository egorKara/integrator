import io
import json
import os
import shutil
import sys
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock
from uuid import uuid4

from app import run


@contextmanager
def project_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_smoke_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class SmokeTest(unittest.TestCase):
    def test_run_returns_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run(["integrator", "doctor"])
        self.assertEqual(code, 0)

    def test_rg_uses_rg_path_env(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"RG_PATH": sys.executable}, clear=False):
            with redirect_stdout(out), redirect_stderr(err):
                code = run(["integrator", "rg", "--no-defaults", "--", "--version"])
        self.assertEqual(code, 0)

    def test_projects_discovery_smoke(self) -> None:
        with project_case_dir() as root:
            project = root / "demo"
            project.mkdir()
            (project / "pyproject.toml").write_text("", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "projects",
                        "list",
                        "--roots",
                        str(root),
                        "--max-depth",
                        "2",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("demo", buf.getvalue())

    def test_agents_only_problems_smoke(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            buf = io.StringIO()
            with mock.patch("agents_ops._is_endpoint_up", return_value=False):
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "agents",
                            "status",
                            "--json",
                            "--only-problems",
                            "--explain",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "3",
                        ]
                    )
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertIn("explain", rows[0])
            self.assertTrue(rows[0]["explain"])

    def test_run_json_strict_smoke(self) -> None:
        with project_case_dir() as root:
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            (root / "tests").mkdir()

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "run",
                        "test",
                        "--cwd",
                        str(root),
                        "--json",
                        "--json-strict",
                        "--dry-run",
                    ]
                )
            self.assertEqual(code, 0)
            lines = [line for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(lines), 1)
            json.loads(lines[0])
