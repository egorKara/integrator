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


def _cmd_perf_baseline(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    python_cmd = sys.executable

    roots = list(args.roots or [])
    max_depth = int(args.max_depth)
    jobs = int(args.jobs)
    report_max_depth = int(args.report_max_depth)

    base: list[str] = [python_cmd, "-m", "integrator"]
    roots_args: list[str] = ["--roots", *roots] if roots else []

    measures: dict[str, Any] = {}

    measures["projects_list"] = _run_timed(base + ["projects", "list", "--max-depth", str(max_depth), *roots_args], cwd)
    measures["status"] = _run_timed(
        base + ["status", "--jobs", str(jobs), "--max-depth", str(max_depth), *roots_args],
        cwd,
    )
    measures["report_json"] = _run_timed(
        base + ["report", "--jobs", str(jobs), "--max-depth", str(report_max_depth), "--json", *roots_args],
        cwd,
    )
    measures["doctor"] = _run_timed(base + ["doctor"], cwd)

    payload: dict[str, Any] = {
        "kind": "perf_baseline",
        "date": _date_iso(),
        "cwd": str(cwd),
        "args": {
            "roots": roots,
            "max_depth": max_depth,
            "jobs": jobs,
            "report_max_depth": report_max_depth,
        },
        "measures": measures,
    }

    out_path = Path(args.write_report).resolve() if args.write_report else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(out_path, payload)
        payload["artifacts"] = {"report": str(out_path)}

    any_failed = any(int(v.get("code", 0)) != 0 for v in measures.values())
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
                _print_tab([name, m.get("code", ""), f'{float(m.get("ms", 0.0)):.3f}ms'])
    return 1 if any_failed else 0


def add_perf_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    perf = sub.add_parser("perf")
    perf_sub = perf.add_subparsers(dest="perf_cmd", required=True)

    baseline = perf_sub.add_parser("baseline")
    baseline.add_argument("--roots", nargs="*", default=None)
    baseline.add_argument("--max-depth", type=int, default=4)
    baseline.add_argument("--jobs", type=int, default=16)
    baseline.add_argument("--report-max-depth", type=int, default=2)
    baseline.add_argument("--write-report", default=f"reports/perf_baseline_{_timestamp_day()}.json")
    baseline.add_argument("--json", action="store_true")
    baseline.set_defaults(func=_cmd_perf_baseline)

