from __future__ import annotations

import io
import json
import shutil
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Iterator
from uuid import uuid4
from unittest import mock

from app import run

RUN_JSON_STRICT_KEYS = {"name", "path", "preset", "commands", "dry_run"}


@contextmanager
def project_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_golden_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class CliContractsGoldenTests(unittest.TestCase):
    def _prepare_python_test_project(self, project: Path) -> None:
        (project / "pyproject.toml").write_text("", encoding="utf-8")
        (project / "tests").mkdir()

    def _assert_json_strict_payload(self, payload: dict[str, object]) -> None:
        self.assertEqual(set(payload.keys()), RUN_JSON_STRICT_KEYS)

    def test_run_json_strict_dry_run_golden_keys(self) -> None:
        with project_case_dir() as project:
            self._prepare_python_test_project(project)

            out = io.StringIO()
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "run",
                        "test",
                        "--cwd",
                        str(project),
                        "--json",
                        "--json-strict",
                        "--dry-run",
                    ]
                )
            self.assertEqual(code, 0)
            line = out.getvalue().strip().splitlines()[0]
            payload = json.loads(line)
            self._assert_json_strict_payload(payload)

    def test_cli_py_size_budget(self) -> None:
        cli_path = Path(__file__).resolve().parents[1] / "cli.py"
        lines = cli_path.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), 340)

    def test_run_json_strict_continue_on_error_stdout_is_valid_jsonl(self) -> None:
        with project_case_dir() as root:
            p1 = root / "p1"
            p2 = root / "p2"
            p1.mkdir()
            p2.mkdir()
            self._prepare_python_test_project(p1)
            self._prepare_python_test_project(p2)

            out = io.StringIO()
            err = io.StringIO()
            state = {"calls": 0}

            def fake_run_capture(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
                if len(cmd) >= 3 and cmd[1:3] == ["-m", "unittest"]:
                    state["calls"] += 1
                    if state["calls"] == 1:
                        return 1, "first fail out\n", "first fail err\n"
                    return 0, "second ok out\n", "second ok err\n"
                return 0, "", ""

            with mock.patch("cli_cmd_run._run_capture", side_effect=fake_run_capture):
                with redirect_stdout(out), redirect_stderr(err):
                    code = run(
                        [
                            "integrator",
                            "run",
                            "test",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "1",
                            "--json",
                            "--json-strict",
                            "--continue-on-error",
                        ]
                    )

            self.assertEqual(code, 1)
            lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            for line in lines:
                obj = json.loads(line)
                self._assert_json_strict_payload(obj)
            self.assertIn("first fail err", err.getvalue())
