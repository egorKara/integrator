import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.ci_contract_smoke import _run_canary_checks, main
from tests.io_capture import capture_stdio


def _valid_payload() -> dict[str, object]:
    return {
        "kind": "session_close_run",
        "contract_version": "1.0",
        "date": "2026-03-04",
        "status": "pass",
        "owner": "AI Agent",
        "task_id": "B16",
        "dry_run": True,
        "reports_dir": "C:\\integrator\\reports",
        "steps": [{"name": "quality", "status": "pass", "details": "ok"}],
        "checks": {"ruff": "pass"},
        "artifacts": {"session_close_json": "C:\\integrator\\reports\\session_close.json"},
        "errors": [],
        "exit_code": 0,
    }


class CIContractSmokeTests(unittest.TestCase):
    def test_run_canary_checks_passes_for_valid_payload(self) -> None:
        errors, validator_errors, matrix = _run_canary_checks(_valid_payload())
        self.assertEqual(errors, [])
        self.assertEqual(validator_errors.get("positive_payload"), [])
        self.assertTrue(bool(validator_errors.get("canary_missing_key")))
        self.assertTrue(bool(validator_errors.get("canary_steps_shape_drift")))
        self.assertTrue(bool(validator_errors.get("canary_exit_status_mismatch")))
        self.assertTrue(bool(validator_errors.get("canary_contract_version_drift")))
        self.assertTrue(bool(validator_errors.get("canary_extra_fields")))
        self.assertIn("positive_payload", matrix)
        self.assertIn("canary_extra_fields", matrix)

    def test_main_json_pass(self) -> None:
        payload = _valid_payload()
        with patch("tools.ci_contract_smoke.subprocess.check_output", return_value=json.dumps(payload)):
            with capture_stdio() as (buf, _err):
                code = main(["--json"])
        self.assertEqual(code, 0)
        row = json.loads(buf.getvalue().strip())
        self.assertEqual(row.get("status"), "pass")
        self.assertIn("validator_errors", row)
        self.assertIn("matrix", row)
        self.assertEqual(row.get("md_path"), "")

    def test_main_json_fail_on_invalid_payload(self) -> None:
        payload = _valid_payload()
        payload.pop("checks")
        with patch("tools.ci_contract_smoke.subprocess.check_output", return_value=json.dumps(payload)):
            with capture_stdio() as (buf, _err):
                code = main(["--json"])
        self.assertEqual(code, 1)
        row = json.loads(buf.getvalue().strip())
        self.assertEqual(row.get("status"), "fail")
        self.assertIn("positive_contract_validation_failed", row.get("errors", []))

    def test_main_writes_markdown_report(self) -> None:
        payload = _valid_payload()
        out_path = Path(__file__).resolve().parent / ".tmp_ci_contract_smoke.md"
        if out_path.exists():
            out_path.unlink()
        with patch("tools.ci_contract_smoke.subprocess.check_output", return_value=json.dumps(payload)):
            with capture_stdio() as (buf, _err):
                code = main(["--json", "--md-path", str(out_path)])
        self.assertEqual(code, 0)
        row = json.loads(buf.getvalue().strip())
        self.assertEqual(row.get("md_path"), str(out_path))
        self.assertTrue(out_path.exists())
        text = out_path.read_text(encoding="utf-8")
        self.assertIn("# CI Contract Smoke", text)
        self.assertIn("status: `pass`", text)
        self.assertIn("## Scenario Matrix", text)
        out_path.unlink(missing_ok=True)
