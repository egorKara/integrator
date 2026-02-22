from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cli_quality


class TestCliQuality(unittest.TestCase):
    def test_tool_version_strips_output(self) -> None:
        with patch.object(cli_quality, "_run_capture", return_value=(0, "x \n", "y \n")):
            r = cli_quality._tool_version(["x"], Path("."))
        self.assertEqual(r["code"], 0)
        self.assertEqual(r["out"], "x")
        self.assertEqual(r["err"], "y")

    def test_coverage_gate_run_failure(self) -> None:
        calls: list[list[str]] = []

        def fake_gate(cmd: list[str], cwd: Path):
            calls.append(cmd)
            return {"code": 2, "out": "no", "err": "bad"}

        with patch.object(cli_quality, "_gate", side_effect=fake_gate):
            r = cli_quality._coverage_gate("python", Path("."), fail_under=80)

        self.assertEqual(r["code"], 2)
        self.assertEqual(r["stage"], "run")
        self.assertTrue(calls)

    def test_coverage_gate_xml_failure_propagates(self) -> None:
        seq = [
            {"code": 0, "out": "ok", "err": ""},
            {"code": 0, "out": "report", "err": ""},
            {"code": 3, "out": "xml", "err": "xmlfail"},
        ]

        def fake_gate(cmd: list[str], cwd: Path):
            return seq.pop(0)

        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            with patch.object(cli_quality, "_gate", side_effect=fake_gate):
                r = cli_quality._coverage_gate("python", cwd, fail_under=80)

        self.assertEqual(r["stage"], "report")
        self.assertEqual(r["code"], 3)
        self.assertEqual(r["xml_code"], 3)

    def test_cmd_quality_summary_writes_report_without_running_gates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "q.json"
                args = argparse.Namespace(json=True, no_run=True, fail_under=80, write_report=str(out_path))

                def fake_run_capture(cmd: list[str], cwd: Path):
                    return 0, "ok", ""

                with patch.object(cli_quality, "_run_capture", side_effect=fake_run_capture):
                    code = cli_quality._cmd_quality_summary(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "quality_summary")
            self.assertEqual(payload["gates"], {})
