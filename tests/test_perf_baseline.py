import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cli


class PerfBaselineTests(unittest.TestCase):
    def test_perf_baseline_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "perf.json"

                def fake_run_capture(cmd: list[str], cwd: Path):
                    return 0, "", ""

                perf_vals = [0.0, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.4]

                def fake_perf_counter():
                    return perf_vals.pop(0)

                with (
                    mock.patch("cli_perf._run_capture", side_effect=fake_run_capture),
                    mock.patch("cli_perf.time.perf_counter", side_effect=fake_perf_counter),
                    mock.patch("cli_perf.time.strftime", return_value="2026-02-22"),
                ):
                    code = cli.run(
                        [
                            "integrator",
                            "perf",
                            "baseline",
                            "--write-report",
                            str(out_path),
                            "--json",
                        ]
                    )
                self.assertEqual(code, 0)
                self.assertTrue(out_path.exists())
                payload = json.loads(out_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["kind"], "perf_baseline")
                self.assertEqual(payload["args"]["roots"], ["."])
                self.assertIn("measures", payload)
                measures = payload["measures"]
                self.assertIn("projects_list", measures)
                pl = measures["projects_list"]
                self.assertIn("summary", pl)
                self.assertIn("runs", pl)
                self.assertFalse(bool(measures["status"]["summary"]["any_failed"]))
            finally:
                os.chdir(prev)

    def test_perf_check_detects_degradation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            baseline_path = Path(td) / "reports" / "baseline.json"
            current_path = Path(td) / "reports" / "current.json"
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_payload = {
                "kind": "perf_baseline",
                "measures": {
                    "projects_list": {"summary": {"median_ms": 100}},
                    "status": {"summary": {"median_ms": 100}},
                    "report_json": {"summary": {"median_ms": 100}},
                    "doctor": {"summary": {"median_ms": 100}},
                },
            }
            current_payload = {
                "kind": "perf_baseline",
                "measures": {
                    "projects_list": {"summary": {"median_ms": 130}},
                    "status": {"summary": {"median_ms": 100}},
                    "report_json": {"summary": {"median_ms": 100}},
                    "doctor": {"summary": {"median_ms": 100}},
                },
            }
            baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False), encoding="utf-8")
            current_path.write_text(json.dumps(current_payload, ensure_ascii=False), encoding="utf-8")

            code = cli.run(
                [
                    "integrator",
                    "perf",
                    "check",
                    "--baseline",
                    str(baseline_path),
                    "--current",
                    str(current_path),
                    "--max-degradation-pct",
                    "20",
                    "--json",
                ]
            )
            self.assertEqual(code, 1)

    def test_perf_baseline_returns_nonzero_when_status_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "perf.json"

                def fake_run_capture(cmd: list[str], cwd: Path):
                    if "status" in cmd:
                        return 1, "", "status failed"
                    return 0, "", ""

                perf_vals = [0.0, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.4]

                def fake_perf_counter():
                    return perf_vals.pop(0)

                with (
                    mock.patch("cli_perf._run_capture", side_effect=fake_run_capture),
                    mock.patch("cli_perf.time.perf_counter", side_effect=fake_perf_counter),
                    mock.patch("cli_perf.time.strftime", return_value="2026-02-22"),
                ):
                    code = cli.run(
                        [
                            "integrator",
                            "perf",
                            "baseline",
                            "--write-report",
                            str(out_path),
                            "--json",
                        ]
                    )
                self.assertEqual(code, 1)
                payload = json.loads(out_path.read_text(encoding="utf-8"))
                self.assertTrue(bool(payload["measures"]["status"]["summary"]["any_failed"]))
            finally:
                os.chdir(prev)
