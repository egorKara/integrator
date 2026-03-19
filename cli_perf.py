from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from utils import _print_json, _print_tab, _run_capture, _write_text_atomic


def _timestamp_day() -> str:
    return time.strftime("%Y%m%d", time.localtime())


def _date_iso() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text_atomic(path, text, backup=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _run_timed(cmd: list[str], cwd: Path) -> dict[str, Any]:
    t0 = time.perf_counter()
    code, out, err = _run_capture(cmd, cwd)
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1000.0
    return {"code": int(code), "ms": ms, "out": out, "err": err}


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return min(values)
    if p >= 1:
        return max(values)
    s = sorted(values)
    idx = int((len(s) - 1) * p)
    return float(s[idx])


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def _run_timed_repeat(cmd: list[str], cwd: Path, repeat: int) -> dict[str, Any]:
    repeat = max(1, int(repeat))
    runs = [_run_timed(cmd, cwd) for _ in range(repeat)]
    ms_values = [float(r.get("ms", 0.0)) for r in runs if isinstance(r, dict)]
    codes = [int(r.get("code", 0)) for r in runs if isinstance(r, dict)]
    summary = {
        "repeat": repeat,
        "min_ms": float(min(ms_values)) if ms_values else 0.0,
        "median_ms": _median(ms_values),
        "p95_ms": _percentile(ms_values, 0.95),
        "max_ms": float(max(ms_values)) if ms_values else 0.0,
        "any_failed": any(code != 0 for code in codes),
    }
    return {"summary": summary, "runs": runs}


def _extract_summary_median(payload: dict[str, Any], metric: str) -> float:
    measures = payload.get("measures", {})
    if not isinstance(measures, dict):
        return 0.0
    node = measures.get(metric, {})
    if not isinstance(node, dict):
        return 0.0
    summary = node.get("summary", {})
    if not isinstance(summary, dict):
        return 0.0
    return float(summary.get("median_ms", 0.0))


def _check_degradation(
    baseline: dict[str, Any], current: dict[str, Any], max_degradation_pct: float
) -> dict[str, Any]:
    metrics = ("projects_list", "status", "report_json", "doctor")
    comparisons: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []
    for metric in metrics:
        base_ms = _extract_summary_median(baseline, metric)
        curr_ms = _extract_summary_median(current, metric)
        if base_ms <= 0:
            ratio_pct = 0.0 if curr_ms <= 0 else 100.0
        else:
            ratio_pct = ((curr_ms - base_ms) / base_ms) * 100.0
        row = {
            "metric": metric,
            "baseline_median_ms": base_ms,
            "current_median_ms": curr_ms,
            "degradation_pct": ratio_pct,
            "degraded": ratio_pct > float(max_degradation_pct),
        }
        comparisons.append(row)
        if row["degraded"]:
            degraded.append(row)
    return {"max_degradation_pct": float(max_degradation_pct), "comparisons": comparisons, "degraded": degraded}


def _cmd_perf_baseline(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    python_cmd = sys.executable

    roots = list(args.roots or ["."])
    max_depth = int(args.max_depth)
    jobs = int(args.jobs)
    report_max_depth = int(args.report_max_depth)
    repeat = int(args.repeat)

    base: list[str] = [python_cmd, "-m", "integrator"]
    roots_args: list[str] = ["--roots", *roots] if roots else []

    measures: dict[str, Any] = {}

    measures["projects_list"] = _run_timed_repeat(
        base + ["projects", "list", "--max-depth", str(max_depth), *roots_args],
        cwd,
        repeat,
    )
    measures["status"] = _run_timed_repeat(
        base + ["status", "--jobs", str(jobs), "--max-depth", str(max_depth), "--limit", "1", *roots_args],
        cwd,
        repeat,
    )
    measures["report_json"] = _run_timed_repeat(
        base + ["report", "--jobs", str(jobs), "--max-depth", str(report_max_depth), "--json", *roots_args],
        cwd,
        repeat,
    )
    measures["doctor"] = _run_timed_repeat(base + ["doctor"], cwd, repeat)

    payload: dict[str, Any] = {
        "kind": "perf_baseline",
        "date": _date_iso(),
        "cwd": str(cwd),
        "args": {
            "roots": roots,
            "max_depth": max_depth,
            "jobs": jobs,
            "report_max_depth": report_max_depth,
            "repeat": repeat,
        },
        "measures": measures,
    }
    degradation_result: dict[str, Any] | None = None
    compare_to_path = str(args.compare_to or "").strip()
    if compare_to_path:
        baseline_payload = _read_json(Path(compare_to_path).resolve())
        degradation_result = _check_degradation(
            baseline_payload,
            payload,
            float(args.max_degradation_pct),
        )
        payload["degradation_check"] = degradation_result

    out_path = Path(args.write_report).resolve() if args.write_report else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, payload)
        payload["artifacts"] = {"report": str(out_path)}

    any_failed = False
    for item in measures.values():
        if not isinstance(item, dict):
            continue
        summary = item.get("summary", {})
        if isinstance(summary, dict) and bool(summary.get("any_failed", False)):
            any_failed = True
    if args.json:
        _print_json(payload)
    else:
        report_path = ""
        artifacts = payload.get("artifacts")
        if isinstance(artifacts, dict):
            report_path = str(artifacts.get("report", ""))
        _print_tab(["report", report_path])
        for name in ("projects_list", "status", "report_json", "doctor"):
            m = measures.get(name, {})
            if isinstance(m, dict):
                summary = m.get("summary", {})
                if isinstance(summary, dict):
                    _print_tab(
                        [
                            name,
                            int(bool(summary.get("any_failed", False))),
                            f'{float(summary.get("median_ms", 0.0)):.3f}ms',
                            f'{float(summary.get("p95_ms", 0.0)):.3f}ms',
                            int(summary.get("repeat", 1)),
                        ]
                    )
        if degradation_result:
            _print_tab(
                [
                    "degradation_check",
                    len(degradation_result.get("degraded", [])),
                    float(degradation_result.get("max_degradation_pct", 0.0)),
                ]
            )
    degraded = []
    if degradation_result:
        maybe_degraded = degradation_result.get("degraded", [])
        if isinstance(maybe_degraded, list):
            degraded = maybe_degraded
    return 1 if any_failed or bool(degraded) else 0


def _cmd_perf_check(args: argparse.Namespace) -> int:
    baseline_path = Path(str(args.baseline)).resolve()
    current_path = Path(str(args.current)).resolve()
    baseline = _read_json(baseline_path)
    current = _read_json(current_path)
    result = _check_degradation(baseline, current, float(args.max_degradation_pct))
    payload: dict[str, Any] = {
        "kind": "perf_degradation_check",
        "baseline_path": str(baseline_path),
        "current_path": str(current_path),
        "result": result,
    }
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["baseline", str(baseline_path)])
        _print_tab(["current", str(current_path)])
        _print_tab(["max_degradation_pct", float(args.max_degradation_pct)])
        for row in result.get("comparisons", []):
            if isinstance(row, dict):
                _print_tab(
                    [
                        str(row.get("metric", "")),
                        f'{float(row.get("baseline_median_ms", 0.0)):.3f}ms',
                        f'{float(row.get("current_median_ms", 0.0)):.3f}ms',
                        f'{float(row.get("degradation_pct", 0.0)):.2f}%',
                        int(bool(row.get("degraded", False))),
                    ]
                )
    return 1 if result.get("degraded") else 0


def add_perf_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    perf = sub.add_parser("perf")
    perf_sub = perf.add_subparsers(dest="perf_cmd", required=True)

    baseline = perf_sub.add_parser("baseline")
    baseline.add_argument("--roots", nargs="*", default=None)
    baseline.add_argument("--max-depth", type=int, default=4)
    baseline.add_argument("--jobs", type=int, default=16)
    baseline.add_argument("--report-max-depth", type=int, default=2)
    baseline.add_argument("--repeat", type=int, default=1)
    baseline.add_argument("--compare-to", default=None)
    baseline.add_argument("--max-degradation-pct", type=float, default=20.0)
    baseline.add_argument("--write-report", default=f"reports/perf_baseline_{_timestamp_day()}.json")
    baseline.add_argument("--json", action="store_true")
    baseline.set_defaults(func=_cmd_perf_baseline)

    check = perf_sub.add_parser("check")
    check.add_argument("--baseline", required=True)
    check.add_argument("--current", required=True)
    check.add_argument("--max-degradation-pct", type=float, default=20.0)
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=_cmd_perf_check)
