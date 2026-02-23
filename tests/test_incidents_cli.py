import os
import tempfile
import unittest
from pathlib import Path

import cli


class IncidentsCliTests(unittest.TestCase):
    def test_incidents_new_writes_file_and_updates_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                docs = Path(td) / "docs"
                (docs / "incidents").mkdir(parents=True, exist_ok=True)
                (docs / "INCIDENT_TEMPLATE.md").write_text(
                    "# Incident: <title>\n\n- ID: <YYYY-MM-DD_short_name>\n- Date: <YYYY-MM-DD>\n- Severity: <p0|p1|p2|p3>\n- Status: <open|mitigated|resolved>\n",
                    encoding="utf-8",
                )
                (docs / "INCIDENTS.md").write_text("# Incidents\n\n## Список\n", encoding="utf-8")

                code = cli.run(
                    [
                        "integrator",
                        "incidents",
                        "new",
                        "--id",
                        "2026-02-22_demo",
                        "--title",
                        "Demo",
                        "--severity",
                        "p1",
                        "--status",
                        "open",
                        "--date",
                        "2026-02-22",
                        "--update-index",
                        "--json",
                    ]
                )
                self.assertEqual(code, 0)

                incident = docs / "incidents" / "2026-02-22_demo.md"
                self.assertTrue(incident.exists())
                content = incident.read_text(encoding="utf-8")
                self.assertIn("Incident: Demo", content)
                self.assertIn("ID: 2026-02-22_demo", content)
                self.assertIn("Date: 2026-02-22", content)
                self.assertIn("Severity: p1", content)

                idx = (docs / "INCIDENTS.md").read_text(encoding="utf-8")
                self.assertIn("(incidents/2026-02-22_demo.md)", idx)
            finally:
                os.chdir(prev)
