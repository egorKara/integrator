from __future__ import annotations
# mypy: disable-error-code=import-not-found

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

try:
    from contract_schemas import validate_session_close_run  # type: ignore[import-not-found]
except ModuleNotFoundError:
    def validate_session_close_run(payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        required = ("contract_version", "status", "exit_code", "checks", "steps")
        for key in required:
            if key not in payload:
                errors.append(f"missing_key:{key}")
        if payload.get("contract_version") != "1.0":
            errors.append("invalid_contract_version")
        status = str(payload.get("status", ""))
        exit_code = payload.get("exit_code")
        if status == "fail" and exit_code == 0:
            errors.append("status_exit_code_mismatch")
        checks = payload.get("checks")
        if not isinstance(checks, list):
            errors.append("invalid_checks_shape")
        steps = payload.get("steps")
        if not isinstance(steps, list):
            errors.append("invalid_steps_shape")
        allowed = set(required)
        extra = [k for k in payload.keys() if k not in allowed]
        if extra:
            errors.append("unexpected_fields")
        return errors


def _load_session_close_payload() -> dict[str, Any]:
    try:
        out = subprocess.check_output(
            ["integrator", "session", "close", "--dry-run", "--json"],
            text=True,
        )
    except OSError:
        out = subprocess.check_output(
            [sys.executable, "-m", "integrator", "session", "close", "--dry-run", "--json"],
            text=True,
        )
    payload = json.loads(out)
    if not isinstance(payload, dict):
        raise ValueError("session_close_payload_not_object")
    return payload


def _run_canary_checks(payload: dict[str, Any]) -> tuple[list[str], dict[str, list[str]], dict[str, dict[str, object]]]:
    errors: list[str] = []
    validator_errors: dict[str, list[str]] = {}
    matrix: dict[str, dict[str, object]] = {}

    positive_errors = validate_session_close_run(payload)
    validator_errors["positive_payload"] = positive_errors
    matrix["positive_payload"] = {"expected_valid": True, "detected": not positive_errors, "validator_errors": positive_errors}
    if positive_errors:
        errors.append("positive_contract_validation_failed")

    bad1 = dict(payload)
    bad1.pop("checks", None)
    bad1_errors = validate_session_close_run(bad1)
    validator_errors["canary_missing_key"] = bad1_errors
    matrix["canary_missing_key"] = {"expected_valid": False, "detected": bool(bad1_errors), "validator_errors": bad1_errors}
    if not bad1_errors:
        errors.append("canary_missing_key_not_detected")

    bad2 = dict(payload)
    bad2["steps"] = [{"name": "x", "status": "pass"}]
    bad2_errors = validate_session_close_run(bad2)
    validator_errors["canary_steps_shape_drift"] = bad2_errors
    matrix["canary_steps_shape_drift"] = {"expected_valid": False, "detected": bool(bad2_errors), "validator_errors": bad2_errors}
    if not bad2_errors:
        errors.append("canary_steps_shape_drift_not_detected")

    bad3 = dict(payload)
    bad3["status"] = "fail"
    bad3["exit_code"] = 0
    bad3_errors = validate_session_close_run(bad3)
    validator_errors["canary_exit_status_mismatch"] = bad3_errors
    matrix["canary_exit_status_mismatch"] = {
        "expected_valid": False,
        "detected": bool(bad3_errors),
        "validator_errors": bad3_errors,
    }
    if not bad3_errors:
        errors.append("canary_exit_status_mismatch_not_detected")

    bad4 = dict(payload)
    bad4["contract_version"] = "2.0"
    bad4_errors = validate_session_close_run(bad4)
    validator_errors["canary_contract_version_drift"] = bad4_errors
    matrix["canary_contract_version_drift"] = {
        "expected_valid": False,
        "detected": bool(bad4_errors),
        "validator_errors": bad4_errors,
    }
    if not bad4_errors:
        errors.append("canary_contract_version_drift_not_detected")

    bad5 = dict(payload)
    bad5["unexpected_field"] = "x"
    bad5_errors = validate_session_close_run(bad5)
    validator_errors["canary_extra_fields"] = bad5_errors
    matrix["canary_extra_fields"] = {"expected_valid": False, "detected": bool(bad5_errors), "validator_errors": bad5_errors}
    if not bad5_errors:
        errors.append("canary_extra_fields_not_detected")

    return errors, validator_errors, matrix


def _render_markdown(
    status: str,
    errors: list[str],
    validator_errors: dict[str, list[str]],
    matrix: dict[str, dict[str, object]],
) -> str:
    lines = ["# CI Contract Smoke", "", f"- status: `{status}`"]
    if errors:
        lines.append(f"- errors: `{', '.join(errors)}`")
    else:
        lines.append("- errors: `none`")
    lines.extend(["", "## Validator Details"])
    for key, value in validator_errors.items():
        if value:
            lines.append(f"- {key}: `{', '.join(value)}`")
        else:
            lines.append(f"- {key}: `ok`")
    lines.extend(["", "## Scenario Matrix"])
    for key, row in matrix.items():
        expected_valid = bool(row.get("expected_valid"))
        detected = bool(row.get("detected"))
        lines.append(f"- {key}: `expected_valid={expected_valid}` `detected={detected}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI smoke for session_close_run contract")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--md-path", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        payload = _load_session_close_payload()
        errors, validator_errors, matrix = _run_canary_checks(payload)
    except Exception as exc:
        if args.json:
            print(json.dumps({"kind": "ci_contract_smoke", "status": "fail", "errors": [str(exc)]}, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1

    status = "pass" if not errors else "fail"
    if args.md_path:
        md_path = Path(str(args.md_path))
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(
            _render_markdown(status=status, errors=errors, validator_errors=validator_errors, matrix=matrix),
            encoding="utf-8",
        )
    if args.json:
        print(
            json.dumps(
                {
                    "kind": "ci_contract_smoke",
                    "status": status,
                    "errors": errors,
                    "validator_errors": validator_errors,
                    "matrix": matrix,
                    "md_path": str(args.md_path) if args.md_path else "",
                },
                ensure_ascii=False,
            )
        )
    else:
        if errors:
            for item in errors:
                print(f"ERROR {item}")
        for key, value in validator_errors.items():
            if value:
                print(f"DETAIL {key}: {','.join(value)}")
        for key, row in matrix.items():
            print(f"MATRIX {key}: expected_valid={bool(row.get('expected_valid'))} detected={bool(row.get('detected'))}")
        print(f"STATUS {status}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
