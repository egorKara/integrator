from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class GateResult:
    ok: bool
    checks: list[dict[str, Any]]
    sli: dict[str, Any]
    errors: list[str]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_payload_not_object:{path}")
    return payload


def _median(payload: dict[str, Any], metric: str) -> float:
    measures = payload.get("measures")
    if not isinstance(measures, dict):
        return 0.0
    node = measures.get(metric)
    if not isinstance(node, dict):
        return 0.0
    summary = node.get("summary")
    if not isinstance(summary, dict):
        return 0.0
    value = summary.get("median_ms")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _perf_degraded(reference_path: Path, current_path: Path, threshold_pct: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ref = _read_json(reference_path)
    cur = _read_json(current_path)
    metrics = ("projects_list", "status", "report_json", "doctor")
    comparisons: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []
    for metric in metrics:
        base = _median(ref, metric)
        now = _median(cur, metric)
        if base <= 0:
            ratio = 0.0
        else:
            ratio = ((now - base) / base) * 100.0
        row = {
            "metric": metric,
            "baseline_median_ms": round(base, 6),
            "current_median_ms": round(now, 6),
            "degradation_pct": round(ratio, 6),
            "degraded": ratio > threshold_pct,
        }
        comparisons.append(row)
        if row["degraded"]:
            degraded.append(row)
    return comparisons, degraded


def _event_sli(events_path: Path) -> dict[str, Any]:
    total = 0
    processed = 0
    task_total = 0
    task_success = 0
    issue_created = 0
    if not events_path.exists():
        return {
            "events_total": 0,
            "events_processed": 0,
            "events_processed_rate": 0.0,
            "task_total": 0,
            "task_success": 0,
            "task_success_rate": 0.0,
            "issue_created_count": 0,
        }
    with events_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("kind") != "telegram_remote_bridge_event":
                continue
            total += 1
            if str(row.get("status", "")).strip().lower() == "processed":
                processed += 1
            text = str(row.get("text", ""))
            if text.startswith("/task"):
                task_total += 1
                if isinstance(row.get("issue_number"), int):
                    task_success += 1
            if isinstance(row.get("issue_number"), int):
                issue_created += 1
    processed_rate = (float(processed) / float(total)) if total > 0 else 0.0
    task_success_rate = (float(task_success) / float(task_total)) if task_total > 0 else 0.0
    return {
        "events_total": total,
        "events_processed": processed,
        "events_processed_rate": round(processed_rate, 6),
        "task_total": task_total,
        "task_success": task_success,
        "task_success_rate": round(task_success_rate, 6),
        "issue_created_count": issue_created,
    }


def _contains_markers(path: Path, markers: Sequence[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(marker in text for marker in markers)


def check_gate(
    *,
    reports_dir: Path,
    docs_dir: Path,
    threshold_pct: float = 20.0,
) -> GateResult:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    docs_dir = docs_dir.resolve()
    reports_dir = reports_dir.resolve()

    execution_json = reports_dir / "rfc_p2_arch_1_execution_plan_2026-03-04.json"
    execution_md = reports_dir / "rfc_p2_arch_1_execution_plan_2026-03-04.md"
    profile_report = reports_dir / "profile_calibration_report_2026-03-06.md"
    perf_report = reports_dir / "perf_reference_baseline_report_2026-03-06.md"
    kickoff_report = reports_dir / "p17_phase1_kickoff_report_2026-03-06.md"
    reference_baseline = reports_dir / "perf_baseline_reference.json"
    current_baseline = reports_dir / "perf_baseline_current.json"
    events_file = reports_dir / "telegram_bridge_events.jsonl"
    rollback_doc = docs_dir / "P17_ROLLBACK.md"

    required_reports = [
        execution_json,
        execution_md,
        profile_report,
        perf_report,
        kickoff_report,
        reference_baseline,
        current_baseline,
    ]
    missing = [str(p) for p in required_reports if not p.exists()]
    if missing:
        errors.append(f"missing_required_artifacts:{','.join(missing)}")
    else:
        checks.append({"name": "required_artifacts_exist", "status": "pass"})

    rollback_ok = _contains_markers(
        rollback_doc,
        ("## Trigger criteria", "## Rollback actions", "## Verification after rollback"),
    )
    if not rollback_ok:
        errors.append("rollback_runbook_missing_or_invalid")
    else:
        checks.append({"name": "rollback_runbook_present", "status": "pass"})

    sli = _event_sli(events_file)
    if int(sli["events_total"]) <= 0:
        errors.append("sli_events_total_zero")
    else:
        checks.append({"name": "sli_events_total", "status": "pass", "value": sli["events_total"]})
    if int(sli["issue_created_count"]) <= 0:
        errors.append("sli_issue_created_zero")
    else:
        checks.append({"name": "sli_issue_created", "status": "pass", "value": sli["issue_created_count"]})
    if float(sli["events_processed_rate"]) < 0.95:
        errors.append(f"sli_events_processed_rate_low:{sli['events_processed_rate']}")
    else:
        checks.append({"name": "sli_events_processed_rate", "status": "pass", "value": sli["events_processed_rate"]})
    if float(sli["task_success_rate"]) < 0.30:
        errors.append(f"sli_task_success_rate_low:{sli['task_success_rate']}")
    else:
        checks.append({"name": "sli_task_success_rate", "status": "pass", "value": sli["task_success_rate"]})

    comparisons: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []
    if reference_baseline.exists() and current_baseline.exists():
        comparisons, degraded = _perf_degraded(reference_baseline, current_baseline, threshold_pct)
        if degraded:
            errors.append(f"perf_degraded:{len(degraded)}")
        else:
            checks.append({"name": "perf_drift_within_threshold", "status": "pass", "threshold_pct": threshold_pct})
    else:
        errors.append("perf_baseline_missing_for_check")
    sli["perf_comparisons"] = comparisons
    sli["perf_degraded_count"] = len(degraded)

    return GateResult(ok=not errors, checks=checks, sli=sli, errors=errors)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P17 phase-1 kickoff gate check")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--max-degradation-pct", type=float, default=20.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        result = check_gate(
            reports_dir=Path(args.reports_dir),
            docs_dir=Path(args.docs_dir),
            threshold_pct=float(args.max_degradation_pct),
        )
    except Exception as exc:
        payload_fail: dict[str, Any] = {"kind": "p17_phase1_gate", "status": "fail", "errors": [str(exc)]}
        if args.json:
            print(json.dumps(payload_fail, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1

    status = "pass" if result.ok else "fail"
    payload_ok: dict[str, Any] = {
        "kind": "p17_phase1_gate",
        "status": status,
        "checks": result.checks,
        "sli": result.sli,
        "errors": result.errors,
    }
    if args.json:
        print(json.dumps(payload_ok, ensure_ascii=False))
    else:
        for check in result.checks:
            print(f"CHECK {check['name']}: {check['status']}")
        for error in result.errors:
            print(f"ERROR {error}")
        print(f"STATUS {status}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
