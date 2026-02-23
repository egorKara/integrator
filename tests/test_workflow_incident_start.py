import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import cli


class WorkflowIncidentStartTests(unittest.TestCase):
    def test_workflow_incident_start_writes_artifacts_and_updates_incident(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                docs = Path(td) / "docs"
                (docs / "incidents").mkdir(parents=True, exist_ok=True)
                (Path(td) / "reports").mkdir(parents=True, exist_ok=True)

                (docs / "INCIDENT_TEMPLATE.md").write_text(
                    "\n".join(
                        [
                            "# Incident: <title>",
                            "",
                            "## Summary",
                            "- ID: <YYYY-MM-DD_short_name>",
                            "- Date: <YYYY-MM-DD>",
                            "- Severity: <p0|p1|p2|p3>",
                            "- Status: <open|mitigated|resolved>",
                            "",
                            "## Verification",
                            "- Commands:",
                            "- Artifacts (`reports/`):",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )
                (docs / "INCIDENTS.md").write_text("## Список\n", encoding="utf-8")

                def fake_run_capture(cmd: list[str], cwd: Path):
                    return 0, "ok", ""

                perf_vals = [0.0, 0.1] * 16

                def fake_perf_counter():
                    return perf_vals.pop(0)

                out = io.StringIO()
                with (
                    mock.patch("cli_quality._run_capture", side_effect=fake_run_capture),
                    mock.patch("cli_perf._run_capture", side_effect=fake_run_capture),
                    mock.patch("cli_perf.time.perf_counter", side_effect=fake_perf_counter),
                    mock.patch("cli_perf.time.strftime", return_value="2026-02-22"),
                    redirect_stdout(out),
                ):
                    code = cli.run(
                        [
                            "integrator",
                            "workflow",
                            "incident",
                            "start",
                            "--id",
                            "2026-02-22_demo",
                            "--title",
                            "Demo",
                            "--severity",
                            "p1",
                            "--status",
                            "open",
                            "--update-index",
                            "--quality-no-run",
                            "--reports-dir",
                            "reports",
                            "--prefix",
                            "t_incident",
                            "--json",
                        ]
                    )

                self.assertEqual(code, 0)
                payload = json.loads(out.getvalue().strip().splitlines()[-1])
                self.assertEqual(payload["kind"], "workflow_incident_start")

                incident_path = Path(payload["artifacts"]["incident_md"])
                self.assertTrue(incident_path.exists())
                incident_text = incident_path.read_text(encoding="utf-8")
                self.assertIn("`python -m integrator perf baseline", incident_text)
                self.assertIn("[perf baseline]", incident_text)
                self.assertIn("[quality summary]", incident_text)

                idx = Path(payload["artifacts"]["index_md"])
                self.assertTrue(idx.exists())
                self.assertIn("2026-02-22_demo", idx.read_text(encoding="utf-8"))

                summary = Path(payload["artifacts"]["summary_json"])
                self.assertTrue(summary.exists())
                perf = Path(payload["artifacts"]["perf_json"])
                self.assertTrue(perf.exists())
                quality = Path(payload["artifacts"]["quality_json"])
                self.assertTrue(quality.exists())
            finally:
                os.chdir(prev)

