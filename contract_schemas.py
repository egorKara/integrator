from __future__ import annotations

from typing import Any

SESSION_CLOSE_RUN_REQUIRED_KEYS = {
    "kind",
    "contract_version",
    "date",
    "status",
    "owner",
    "task_id",
    "dry_run",
    "reports_dir",
    "steps",
    "checks",
    "artifacts",
    "errors",
    "exit_code",
}


def validate_session_close_run(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    keys = set(payload.keys())
    if keys != SESSION_CLOSE_RUN_REQUIRED_KEYS:
        missing = sorted(SESSION_CLOSE_RUN_REQUIRED_KEYS - keys)
        extra = sorted(keys - SESSION_CLOSE_RUN_REQUIRED_KEYS)
        if missing:
            errors.append(f"missing_keys:{','.join(missing)}")
        if extra:
            errors.append(f"extra_keys:{','.join(extra)}")

    if payload.get("kind") != "session_close_run":
        errors.append("kind:not_session_close_run")
    if payload.get("contract_version") != "1.0":
        errors.append("contract_version:not_1_0")

    status = payload.get("status")
    if status not in {"pass", "fail"}:
        errors.append("status:not_pass_or_fail")

    dry_run = payload.get("dry_run")
    if not isinstance(dry_run, bool):
        errors.append("dry_run:not_bool")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks:not_dict")
    else:
        bad_checks = [k for k, v in checks.items() if not isinstance(k, str) or not isinstance(v, str)]
        if bad_checks:
            errors.append("checks:not_str_dict")

    steps = payload.get("steps")
    if not isinstance(steps, list):
        errors.append("steps:not_list")
    else:
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"steps[{i}]:not_object")
                continue
            if set(step.keys()) != {"name", "status", "details"}:
                errors.append(f"steps[{i}]:invalid_keys")
                continue
            if not all(isinstance(step.get(k), str) for k in ("name", "status", "details")):
                errors.append(f"steps[{i}]:non_str_fields")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts:not_dict")

    report_errors = payload.get("errors")
    if not isinstance(report_errors, list) or any(not isinstance(x, str) for x in report_errors):
        errors.append("errors:not_str_list")

    exit_code = payload.get("exit_code")
    if not isinstance(exit_code, int):
        errors.append("exit_code:not_int")
    else:
        if status == "pass" and exit_code != 0:
            errors.append("exit_code_status_mismatch:pass_nonzero")
        if status == "fail" and exit_code == 0:
            errors.append("exit_code_status_mismatch:fail_zero")

    return errors
