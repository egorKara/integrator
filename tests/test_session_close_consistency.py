import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_session_close_consistency as mod


def _write_session_artifacts(root: Path, date: str = "2026-03-04") -> Path:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    tracker = reports / f"priority_execution_tracker_{date}.csv"
    report = reports / f"priority_execution_report_{date}.md"
    session_json = reports / f"session_close_{date}.json"
    session_md = reports / f"session_close_{date}.md"

    tracker.write_text("task_id,status\nB1,completed\n", encoding="utf-8")
    report.write_text("# Priority execution report\n", encoding="utf-8")
    session_md.write_text(
        "\n".join(
            [
                f"# Session close ({date})",
                "## Тезис",
                "- ok",
                "## Антитезис",
                "- risk",
                "## Синтез",
                "- plan",
                "### Уроки",
                "- lesson",
                "### Next atomic step",
                "- step",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payload = {
        "kind": "session_close",
        "date": date,
        "owner": "agent",
        "status": "closed",
        "scope": {
            "tracker": f"reports/priority_execution_tracker_{date}.csv",
            "execution_report": f"reports/priority_execution_report_{date}.md",
        },
        "thesis": "t",
        "antithesis": ["a"],
        "synthesis": ["s"],
        "lessons": ["l"],
        "next_atomic_step": "n",
        "verification": {"json_parse": "pass"},
        "risks_next": [{"id": "R1"}],
        "artifacts": [
            f"reports/session_close_{date}.json",
            f"reports/session_close_{date}.md",
            f"reports/priority_execution_tracker_{date}.csv",
            f"reports/priority_execution_report_{date}.md",
        ],
    }
    session_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return reports


class SessionCloseConsistencyTests(unittest.TestCase):
    def test_check_consistency_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = _write_session_artifacts(Path(td))
            result = mod.check_consistency(reports_dir=reports)
        self.assertTrue(result.ok)
        self.assertEqual(result.date, "2026-03-04")
        self.assertEqual(result.errors, [])

    def test_check_consistency_missing_json_field(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = _write_session_artifacts(Path(td))
            session_json = reports / "session_close_2026-03-04.json"
            payload = json.loads(session_json.read_text(encoding="utf-8"))
            del payload["verification"]
            session_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result = mod.check_consistency(reports_dir=reports)
        self.assertFalse(result.ok)
        self.assertTrue(any(err.startswith("missing_json_fields:") for err in result.errors))

    def test_main_json_output_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = _write_session_artifacts(Path(td))
            (reports / "priority_execution_report_2026-03-04.md").unlink()
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                code = mod.main(["--reports-dir", str(reports), "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "session_close_consistency")
        self.assertEqual(payload["status"], "fail")
        self.assertTrue(payload["errors"])

    def test_main_uses_explicit_date(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = _write_session_artifacts(root, date="2026-03-03")
            _write_session_artifacts(root, date="2026-03-04")
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = mod.main(["--reports-dir", str(reports), "--date", "2026-03-03"])
        self.assertEqual(code, 0)
        self.assertIn("session_close_date=2026-03-03", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
