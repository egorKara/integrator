from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from utils import _print_json, _print_tab, _run_capture, _write_text_atomic


def _tool_version(cmd: list[str], cwd: Path) -> dict[str, Any]:
    code, out, err = _run_capture(cmd, cwd)
    return {"code": code, "out": out.strip(), "err": err.strip()}


def _gate(cmd: list[str], cwd: Path) -> dict[str, Any]:
    code, out, err = _run_capture(cmd, cwd)
    return {"code": code, "out": out.strip(), "err": err.strip()}


def _coverage_gate(python_cmd: str, cwd: Path, fail_under: int) -> dict[str, Any]:
    reports_dir = (cwd / "reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    run = _gate(
        [python_cmd, "-m", "coverage", "run", "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"],
        cwd,
    )
    if run["code"] != 0:
        return {"code": int(run["code"]), "stage": "run", "out": run["out"], "err": run["err"]}

    report = _gate(
        [python_cmd, "-m", "coverage", "report", "-m", "--fail-under", str(int(fail_under))],
        cwd,
    )
    xml = _gate([python_cmd, "-m", "coverage", "xml", "-o", str(reports_dir / "coverage.xml")], cwd)

    code = int(report["code"]) if int(report["code"]) != 0 else int(xml["code"])
    return {
        "code": code,
        "stage": "report",
        "out": report["out"],
        "err": report["err"],
        "xml_code": int(xml["code"]),
        "xml_err": xml["err"],
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text_atomic(path, text, backup=True)


def _cmd_quality_summary(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    python_cmd = sys.executable

    tools = {
        "python": {"executable": python_cmd, "version": sys.version.split()[0], "version_full": sys.version},
        "git": _tool_version(["git", "--version"], cwd),
        "ruff": _tool_version([python_cmd, "-m", "ruff", "--version"], cwd),
        "mypy": _tool_version([python_cmd, "-m", "mypy", "--version"], cwd),
        "coverage": _tool_version([python_cmd, "-m", "coverage", "--version"], cwd),
    }

    gates: dict[str, Any] = {}
    if not args.no_run:
        gates["ruff"] = _gate([python_cmd, "-m", "ruff", "check", "."], cwd)
        gates["mypy"] = _gate([python_cmd, "-m", "mypy", "."], cwd)
        gates["unittest"] = _gate([python_cmd, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"], cwd)
        gates["coverage"] = _coverage_gate(python_cmd, cwd, int(args.fail_under))

    artifacts = {
        "coverage_xml": str((cwd / "reports" / "coverage.xml").resolve()),
        "security_gitleaks_json": str((cwd / "reports" / "gitleaks.json").resolve()),
        "security_pip_audit_requirements_json": str((cwd / "reports" / "pip-audit-requirements.json").resolve()),
        "security_pip_audit_operator_json": str((cwd / "reports" / "pip-audit-operator.json").resolve()),
    }

    payload: dict[str, Any] = {
        "kind": "quality_summary",
        "cwd": str(cwd),
        "tools": tools,
        "gates": gates,
        "artifacts": artifacts,
    }

    out_path = Path(args.write_report).resolve() if args.write_report else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_report(out_path, payload)

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["cwd", payload["cwd"]])
        _print_tab(["python", tools["python"]["executable"], tools["python"]["version"]])
        for name in ("git", "ruff", "mypy", "coverage"):
            tv = tools[name]
            _print_tab([name, tv["code"], tv["out"] or tv["err"]])
        if gates:
            for name in ("ruff", "mypy", "unittest", "coverage"):
                gv = gates.get(name, {})
                _print_tab([f"gate:{name}", gv.get("code", ""), (gv.get("out") or gv.get("err") or "")])
        _print_tab(["coverage.xml", artifacts["coverage_xml"]])
    any_failed = any(int(v.get("code", 0)) != 0 for v in gates.values()) if gates else False
    return 1 if any_failed else 0


def add_quality_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    quality = sub.add_parser("quality")
    quality_sub = quality.add_subparsers(dest="quality_cmd", required=True)

    summary = quality_sub.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    summary.add_argument("--no-run", action="store_true")
    summary.add_argument("--fail-under", type=int, default=80)
    summary.add_argument("--write-report", default=None)
    summary.set_defaults(func=_cmd_quality_summary)
