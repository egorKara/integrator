import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import ensure_daily_priority_template as mod


class EnsureDailyPriorityTemplateTests(unittest.TestCase):
    def test_ensure_template_adds_block_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "reports" / "github_project_backlog_execution_2026-03-07.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("# Demo\n", encoding="utf-8")
            first = mod.ensure_template(report, "2026-03-07")
            second = mod.ensure_template(report, "2026-03-07")
            text = report.read_text(encoding="utf-8")
        self.assertTrue(first["added"])
        self.assertFalse(second["added"])
        self.assertEqual(text.count("## Ежедневный шаблон приоритизации P0/P1/P2"), 1)

    def test_main_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = mod.main(["--reports-dir", str(reports), "--date", "2026-03-07", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertTrue(str(payload["report"]).endswith(".md"))


if __name__ == "__main__":
    unittest.main()
