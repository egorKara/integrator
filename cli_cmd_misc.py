from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from chains import chain_rows, load_chains
from cli_env import _diagnostics_rows, _print_python_status, _print_root_status, _print_tool_status, default_roots
from registry import load_registry, registry_rows
from run_ops import _resolve_python_command
from services_preflight import default_lm_studio_base_url, lm_models_url, rag_health_url, try_start_lm_studio, try_start_rag
from utils import _print_json, _print_tab, _run_command


def _cmd_doctor(_: argparse.Namespace) -> int:
    _print_tool_status("git")
    _print_python_status()
    _print_root_status(Path(r"C:\vault\Projects"))
    _print_root_status(Path(r"C:\LocalAI"))
    return 0


def _cmd_diagnostics(args: argparse.Namespace) -> int:
    roots = [Path(p) for p in args.roots] if args.roots else default_roots()
    rows = _diagnostics_rows(roots)
    if args.only_problems:
        rows = [row for row in rows if row.get("status") != "ok"]

    any_failed = any(row.get("status") != "ok" for row in rows)
    for row in rows:
        if args.json:
            _print_json(row)
        else:
            _print_tab([row["kind"], row["name"], row["status"], row["path"]])
    return 1 if any_failed else 0


def _cmd_preflight(args: argparse.Namespace) -> int:
    import cli as cli_module

    check_only = bool(args.check_only)
    any_failed = False

    rag_cwd = Path(args.rag_cwd).resolve()
    rag_base_url = str(args.rag_base_url).strip() or "http://127.0.0.1:8011"
    rag_url = rag_health_url(rag_base_url)
    rag_started = False
    rag_start_error = ""

    rag_check = cli_module.wait_ready(rag_url, timeout_sec=2.0, attempts=1, sleep_sec=0.0)
    if not rag_check.ok and not check_only:
        python_cmd = _resolve_python_command(rag_cwd)
        if python_cmd:
            rag_started, rag_start_error = try_start_rag(python_cmd, rag_cwd, base_url=rag_base_url)
            rag_check = cli_module.wait_ready(rag_url, timeout_sec=2.0, attempts=20, sleep_sec=0.25)
        else:
            rag_start_error = "python_not_found"
    rag_ok = bool(rag_check.ok)
    if not rag_ok:
        any_failed = True

    lm_base_url = str(args.lm_base_url).strip() or default_lm_studio_base_url()
    lm_url = lm_models_url(lm_base_url)
    lm_started = False
    lm_start_error = ""

    lm_check = cli_module.wait_ready(lm_url, timeout_sec=2.0, attempts=1, sleep_sec=0.0)
    if not lm_check.ok and not check_only:
        lm_started, lm_start_error = try_start_lm_studio()
        lm_check = cli_module.wait_ready(lm_url, timeout_sec=2.0, attempts=20, sleep_sec=0.25)
    lm_ok = bool(lm_check.ok)
    if not lm_ok:
        any_failed = True

    payload = {
        "kind": "preflight",
        "rag": {
            "ok": rag_ok,
            "url": rag_url,
            "status": int(rag_check.status),
            "started": bool(rag_started),
            "start_error": rag_start_error or "",
            "error": rag_check.error or "",
        },
        "lm_studio": {
            "ok": lm_ok,
            "url": lm_url,
            "status": int(lm_check.status),
            "started": bool(lm_started),
            "start_error": lm_start_error or "",
            "error": lm_check.error or "",
        },
    }

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["rag", int(rag_ok), rag_check.status, int(rag_started), rag_url, rag_check.error or rag_start_error])
        _print_tab(["lm_studio", int(lm_ok), lm_check.status, int(lm_started), lm_url, lm_check.error or lm_start_error])

    return 1 if any_failed else 0


def _cmd_exec(args: argparse.Namespace) -> int:
    if not args.command:
        print("command is required", file=sys.stderr)
        return 2
    cwd = Path(args.cwd)
    return _run_command(args.command, cwd)


def _resolve_rg_exe() -> str | None:
    env_path = os.environ.get("RG_PATH", "").strip()
    if env_path and Path(env_path).is_file():
        return env_path

    which = shutil.which("rg")
    if which:
        return which

    localappdata = os.environ.get("LOCALAPPDATA", "").strip()
    if localappdata:
        candidate = (
            Path(localappdata)
            / "Programs"
            / "Trae"
            / "resources"
            / "app"
            / "node_modules"
            / "@vscode"
            / "ripgrep"
            / "bin"
            / "rg.exe"
        )
        if candidate.is_file():
            return str(candidate)
    return None


def _cmd_rg(args: argparse.Namespace) -> int:
    rg = _resolve_rg_exe()
    if not rg:
        print("rg not found (set RG_PATH or install ripgrep in PATH)", file=sys.stderr)
        return 127

    cwd = Path(args.cwd).resolve()
    rest = list(args.args or [])
    if rest and rest[0] == "--":
        rest = rest[1:]

    cmd: list[str] = [rg]
    if not args.no_defaults:
        cmd.extend(["-n", "--hidden", "--glob", "!.git", "--glob", "!vault", "--glob", "!.trae"])

    if rest:
        cmd.extend(rest)
    else:
        cmd.append("--help")

    return _run_command(cmd, cwd)


def _cmd_registry_list(args: argparse.Namespace) -> int:
    path = Path(args.registry).resolve() if args.registry else None
    entries = load_registry(path)
    rows = registry_rows(entries)
    for row in rows:
        if args.json:
            _print_json(row)
        else:
            tags_value = row.get("tags", [])
            tags_list = tags_value if isinstance(tags_value, list) else []
            _print_tab(
                [
                    row.get("name", ""),
                    row.get("root", ""),
                    row.get("status", ""),
                    row.get("priority", ""),
                    row.get("entrypoint", ""),
                    ",".join([str(item) for item in tags_list if str(item)]),
                ]
            )
    return 0


def _cmd_chains_list(args: argparse.Namespace) -> int:
    path = Path(args.chains).resolve() if args.chains else None
    chains = load_chains(path)
    rows = chain_rows(chains)
    for row in rows:
        if args.json:
            _print_json(row)
        else:
            steps_value = row.get("steps", [])
            steps_list = steps_value if isinstance(steps_value, list) else []
            _print_tab([row.get("name", ""), row.get("description", ""), str(len(steps_list))])
    return 0


def _cmd_chains_plan(args: argparse.Namespace) -> int:
    path = Path(args.chains).resolve() if args.chains else None
    chains = load_chains(path)
    chain = next((item for item in chains if item.name == args.name), None)
    if not chain:
        print("chain not found", file=sys.stderr)
        return 2
    steps = [list(step) for step in chain.steps]
    if args.json:
        _print_json({"name": chain.name, "description": chain.description, "steps": steps})
    else:
        _print_tab([chain.name, chain.description])
        for step in steps:
            print("  " + " ".join(step))
    return 0
