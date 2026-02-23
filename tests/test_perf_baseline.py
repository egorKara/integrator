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
                self.assertIn("measures", payload)
                measures = payload["measures"]
                self.assertIn("projects_list", measures)
                pl = measures["projects_list"]
                self.assertIn("summary", pl)
                self.assertIn("runs", pl)
            finally:
                os.chdir(prev)
