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
    return 1 if any_failed else 0


def add_perf_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    perf = sub.add_parser("perf")
    perf_sub = perf.add_subparsers(dest="perf_cmd", required=True)

    baseline = perf_sub.add_parser("baseline")
    baseline.add_argument("--roots", nargs="*", default=None)
    baseline.add_argument("--max-depth", type=int, default=4)
    baseline.add_argument("--jobs", type=int, default=16)
    baseline.add_argument("--report-max-depth", type=int, default=2)
    baseline.add_argument("--repeat", type=int, default=1)
    baseline.add_argument("--write-report", default=f"reports/perf_baseline_{_timestamp_day()}.json")
    baseline.add_argument("--json", action="store_true")
    baseline.set_defaults(func=_cmd_perf_baseline)
