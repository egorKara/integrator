import json
import tempfile
import unittest
from pathlib import Path

from tools import check_p17_phase1_gate as mod


def _write_perf(path: Path, value: float) -> None:
    payload = {
        "kind": "perf_baseline",
        "measures": {
            "projects_list": {"summary": {"median_ms": value}},
            "status": {"summary": {"median_ms": value}},
            "report_json": {"summary": {"median_ms": value}},
            "doctor": {"summary": {"median_ms": value}},
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_required_files(reports: Path, docs: Path) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    for name in (
        "rfc_p2_arch_1_execution_plan_2026-03-04.json",
        "rfc_p2_arch_1_execution_plan_2026-03-04.md",
        "profile_calibration_report_2026-03-06.md",
        "perf_reference_baseline_report_2026-03-06.md",
        "p17_phase1_kickoff_report_2026-03-06.md",
    ):
        (reports / name).write_text("ok\n", encoding="utf-8")
    _write_perf(reports / "perf_baseline_reference.json", 100.0)
    _write_perf(reports / "perf_baseline_current.json", 105.0)
    (reports / "telegram_bridge_events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "kind": "telegram_remote_bridge_event",
                        "status": "processed",
                        "text": "/task x",
                        "issue_number": 27,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "kind": "telegram_remote_bridge_event",
                        "status": "processed",
                        "text": "/status",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (docs / "P17_ROLLBACK.md").write_text(
        "\n".join(
            [
                "# P17 Rollback",
                "## Trigger criteria",
                "- drift",
                "## Rollback actions",
                "- rollback",
                "## Verification after rollback",
                "- verify",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class P17Phase1GateTests(unittest.TestCase):
    def test_check_gate_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            docs = root / "docs"
            _write_required_files(reports, docs)
            result = mod.check_gate(reports_dir=reports, docs_dir=docs, threshold_pct=20.0)
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])
        self.assertGreaterEqual(int(result.sli.get("issue_created_count", 0)), 1)

    def test_check_gate_fails_on_perf_degradation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            docs = root / "docs"
            _write_required_files(reports, docs)
            _write_perf(reports / "perf_baseline_current.json", 150.0)
            result = mod.check_gate(reports_dir=reports, docs_dir=docs, threshold_pct=20.0)
        self.assertFalse(result.ok)
        self.assertTrue(any(err.startswith("perf_degraded:") for err in result.errors))


if __name__ == "__main__":
    unittest.main()
