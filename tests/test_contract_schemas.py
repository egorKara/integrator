import unittest
from typing import Any

from contract_schemas import validate_session_close_run


def _valid_payload() -> dict[str, Any]:
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
        "checks": {"ruff": "pass", "mypy": "pass"},
        "artifacts": {"session_close_json": "C:\\integrator\\reports\\session_close.json"},
        "errors": [],
        "exit_code": 0,
    }


class ContractSchemasTests(unittest.TestCase):
    def test_validate_session_close_run_accepts_valid_payload(self) -> None:
        payload = _valid_payload()
        self.assertEqual(validate_session_close_run(payload), [])

    def test_validate_session_close_run_detects_missing_key(self) -> None:
        payload = _valid_payload()
        payload.pop("checks")
        errors = validate_session_close_run(payload)
        self.assertTrue(any(e.startswith("missing_keys:") for e in errors))

    def test_validate_session_close_run_detects_step_shape_drift(self) -> None:
        payload = _valid_payload()
        payload["steps"] = [{"name": "quality", "status": "pass"}]
        errors = validate_session_close_run(payload)
        self.assertIn("steps[0]:invalid_keys", errors)

    def test_validate_session_close_run_detects_exit_status_mismatch(self) -> None:
        payload = _valid_payload()
        payload["status"] = "fail"
        payload["exit_code"] = 0
        errors = validate_session_close_run(payload)
        self.assertIn("exit_code_status_mismatch:fail_zero", errors)
