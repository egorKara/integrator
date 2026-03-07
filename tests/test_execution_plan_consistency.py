import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_execution_plan_consistency as mod


def _write_plan_pair(root: Path, date: str = "2026-03-04") -> Path:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / f"demo_execution_plan_{date}.json"
    md_path = reports / f"demo_execution_plan_{date}.md"
    source = reports / "source.md"
    source.write_text("# source\n", encoding="utf-8")
    payload = {
        "plan_id": f"DEMO-EXEC-{date}",
        "title": "Demo plan",
        "status": "approved_for_execution",
        "created_at": date,
        "source_report": "reports/source.md",
        "items": [{"id": "I1", "title": "do"}],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# Demo Execution Plan {date}",
                f"- Plan ID: `{payload['plan_id']}`",
                f"- JSON-источник: `reports/{json_path.name}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return reports


class ExecutionPlanConsistencyTests(unittest.TestCase):
    def test_check_consistency_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = _write_plan_pair(Path(td))
            result = mod.check_consistency(reports_dir=reports)
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.checked_pairs), 1)

    def test_check_consistency_orphan_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = _write_plan_pair(Path(td))
            (reports / "demo_execution_plan_2026-03-04.json").unlink()
            result = mod.check_consistency(reports_dir=reports)
        self.assertFalse(result.ok)
        self.assertTrue(any(err.startswith("orphan_md:") for err in result.errors))

    def test_main_json_output_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = _write_plan_pair(Path(td))
            md_path = reports / "demo_execution_plan_2026-03-04.md"
            md_path.write_text("# broken\n", encoding="utf-8")
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = mod.main(["--reports-dir", str(reports), "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "execution_plan_consistency")
        self.assertEqual(payload["status"], "fail")
        self.assertTrue(payload["errors"])


if __name__ == "__main__":
    unittest.main()
