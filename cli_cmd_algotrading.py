from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from cli_env import default_localai_assistant_root, default_vault_root
from run_ops import _resolve_python_command
from utils import _print_json, _print_tab, _read_text, _write_text_atomic


def _default_assistant_root() -> Path:
    return default_localai_assistant_root()


def _default_vault_algotrading_root() -> Path:
    env = os.environ.get("ALGO_VAULT_ROOT", "").strip()
    if env:
        return Path(env).resolve()

    base = default_vault_root()
    candidate_projects = (base / "Projects" / "AlgoTrading").resolve()
    if candidate_projects.exists():
        return candidate_projects

    return (base / "AlgoTrading").resolve()


def _default_config_path(vault_root: Path) -> Path:
    return (vault_root / "Configs" / "algotrading.json").resolve()


def _load_config(path: Path) -> dict[str, object]:
    text = _read_text(path) or ""
    if not text.strip():
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    return {str(k): v for k, v in obj.items()}


def _config_env(cfg: dict[str, object]) -> dict[str, str]:
    raw = cfg.get("env", {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        key = str(k).strip()
        if not key:
            continue
        if v is None:
            continue
        out[key] = str(v)
    return out


def _env_from_file(path: Path) -> dict[str, str]:
    text = _read_text(path) or ""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        if "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            continue
        out[key] = val
    return out


def _run_python(
    python_cmd: str,
    cwd: Path,
    argv: list[str],
    *,
    extra_env: dict[str, str] | None,
) -> tuple[int, str, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    cmd = [python_cmd, *argv]
    try:
        completed = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
        return int(completed.returncode), completed.stdout, completed.stderr
    except FileNotFoundError:
        return 127, "", f"tool not found: {cmd[0]}"
    except OSError as exc:
        return 1, "", str(exc)


def _cmd_algotrading_doctor(args: argparse.Namespace) -> int:
    assistant_root = Path(args.assistant_root).resolve()
    vault_root = Path(args.vault_root).resolve()
    config_path = Path(args.config).resolve() if getattr(args, "config", None) else _default_config_path(vault_root)

    checks: list[dict[str, object]] = []

    def add(kind: str, name: str, path: Path, required: bool = True) -> None:
        ok = path.exists()
        checks.append(
            {
                "kind": kind,
                "name": name,
                "path": str(path),
                "required": bool(required),
                "ok": bool(ok),
            }
        )

    add("assistant", "root", assistant_root, True)
    add("assistant", "scripts/run_algo.py", assistant_root / "scripts" / "run_algo.py", True)
    add("assistant", "scripts/optimize_lessons.py", assistant_root / "scripts" / "optimize_lessons.py", True)
    add("assistant", "scripts/media_db_migrate.py", assistant_root / "scripts" / "media_db_migrate.py", True)
    add("assistant", "docs/API_Reference.md", assistant_root / "docs" / "API_Reference.md", False)
    add("assistant", "docs/RAG_Service.md", assistant_root / "docs" / "RAG_Service.md", False)
    add("assistant", "docs/Algotrading_Pipeline.md", assistant_root / "docs" / "Algotrading_Pipeline.md", False)
    add("vault", "AlgoTrading vault", vault_root, True)
    add("vault", "SPEC-001-Pipeline.md", vault_root / "Specs" / "SPEC-001-Pipeline.md", False)
    add("vault", "REQ-001-User-Feedback.md", vault_root / "Specs" / "REQ-001-User-Feedback.md", False)
    add("vault", "Configs/algotrading.json", config_path, False)

    python_cmd = _resolve_python_command(assistant_root) or ""
    python_ok = bool(python_cmd)

    required_failed = any((not bool(row["ok"])) and bool(row["required"]) for row in checks)
    pipeline_doc_missing = not (assistant_root / "docs" / "Algotrading_Pipeline.md").exists()

    payload = {
        "kind": "algotrading_doctor",
        "assistant_root": str(assistant_root),
        "vault_root": str(vault_root),
        "config_path": str(config_path),
        "assistant_python": python_cmd,
        "assistant_python_ok": python_ok,
        "checks": checks,
        "notes": {
            "pipeline_doc_missing": bool(pipeline_doc_missing),
            "suggest_sync_ssot": bool(pipeline_doc_missing and assistant_root.exists() and vault_root.exists()),
        },
    }

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["assistant_root", str(assistant_root)])
        _print_tab(["vault_root", str(vault_root)])
        _print_tab(["assistant_python", python_cmd or ""])
        for row in checks:
            _print_tab([row["kind"], row["name"], int(bool(row["ok"])), row["path"]])
        if pipeline_doc_missing:
            _print_tab(["hint", "docs/Algotrading_Pipeline.md missing; try: integrator algotrading sync-ssot"])

    return 1 if required_failed else 0


def _cmd_algotrading_sync_ssot(args: argparse.Namespace) -> int:
    assistant_root = Path(args.assistant_root).resolve()
    vault_root = Path(args.vault_root).resolve()

    spec_path = vault_root / "Specs" / "SPEC-001-Pipeline.md"
    req_path = vault_root / "Specs" / "REQ-001-User-Feedback.md"
    readme_path = vault_root / "README.md"

    assistant_docs = assistant_root / "docs"
    assistant_docs.mkdir(parents=True, exist_ok=True)
    out_path = assistant_docs / "Algotrading_Pipeline.md"

    if out_path.exists() and not bool(args.force):
        payload = {"kind": "algotrading_sync_ssot", "status": "skipped_exists", "path": str(out_path)}
        if args.json:
            _print_json(payload)
        else:
            _print_tab(["status", "skipped_exists"])
            _print_tab(["path", str(out_path)])
        return 0

    parts: list[str] = []
    parts.append("# Algotrading Pipeline (SSOT Mirror)")
    parts.append("")
    parts.append("Этот файл автоматически синхронизирован из Obsidian‑vault AlgoTrading.")
    parts.append("")

    readme = _read_text(readme_path) or ""
    if readme.strip():
        parts.append("## Vault README (excerpt)")
        parts.append("")
        parts.append(readme.strip()[:2000].rstrip())
        parts.append("")

    spec = _read_text(spec_path) or ""
    if spec.strip():
        parts.append("## SPEC-001-Pipeline (excerpt)")
        parts.append("")
        parts.append(spec.strip()[:6000].rstrip())
        parts.append("")

    req = _read_text(req_path) or ""
    if req.strip():
        parts.append("## REQ-001-User-Feedback (excerpt)")
        parts.append("")
        parts.append(req.strip()[:4000].rstrip())
        parts.append("")

    text = "\n".join(parts).rstrip() + "\n"

    try:
        _write_text_atomic(out_path, text, backup=True)
    except OSError as exc:
        payload = {"kind": "algotrading_sync_ssot", "status": "error", "error": str(exc), "path": str(out_path)}
        if args.json:
            _print_json(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 1

    payload = {"kind": "algotrading_sync_ssot", "status": "written", "path": str(out_path)}
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["status", "written"])
        _print_tab(["path", str(out_path)])
    return 0


def _cmd_algotrading_config_init(args: argparse.Namespace) -> int:
    vault_root = Path(args.vault_root).resolve()
    config_path = Path(args.path).resolve() if args.path else _default_config_path(vault_root)
    if config_path.exists() and not bool(args.force):
        payload = {"kind": "algotrading_config_init", "status": "skipped_exists", "path": str(config_path)}
        if args.json:
            _print_json(payload)
        else:
            _print_tab(["status", "skipped_exists"])
            _print_tab(["path", str(config_path)])
        return 0

    out_dir = ""
    if bool(getattr(args, "fill_from_vault", False)):
        out_dir = str((vault_root / "processed").resolve())

    kb_root = str((Path(out_dir) / "KB").resolve()) if out_dir else ""
    reports_root = str((Path(out_dir) / "Reports").resolve()) if out_dir else ""

    cfg: dict[str, object] = {
        "vault_root": str(vault_root),
        "assistant_root": str(_default_assistant_root()),
        "base_dir": "",
        "out_dir": out_dir,
        "env": {
            "ALGO_METHOD_AUTO": "1",
            "ALGO_SHOT_MODE": "smart",
            "ALGO_TRANSCRIBE_MODE": "faster",
        },
        "optimize_lessons": {
            "source": out_dir,
            "output": kb_root,
            "reports": reports_root,
            "write_versions": True,
            "no_index": False,
        },
        "media_db_migrate": {
            "source": "",
            "target": "",
            "report_dir": reports_root,
            "stage": "all",
            "approve_dedup": False,
            "dedup_mode": None,
            "backup_mode": None,
            "backup_dir": "",
            "dry_run": True,
            "move": False,
        },
    }

    if out_dir:
        env = cfg.get("env")
        if isinstance(env, dict):
            env["ALGO_LESSONS_SOURCE"] = out_dir
            env["ALGO_LESSONS_OUTPUT"] = kb_root
            env["ALGO_LESSONS_REPORTS"] = reports_root

    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    try:
        _write_text_atomic(config_path, text, backup=True)
    except OSError as exc:
        payload = {"kind": "algotrading_config_init", "status": "error", "error": str(exc), "path": str(config_path)}
        if args.json:
            _print_json(payload)
        else:
            print(str(exc), file=sys.stderr)
        return 1

    payload = {"kind": "algotrading_config_init", "status": "written", "path": str(config_path)}
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["status", "written"])
        _print_tab(["path", str(config_path)])
    return 0


def _cmd_algotrading_config_show(args: argparse.Namespace) -> int:
    vault_root = Path(args.vault_root).resolve()
    config_path = Path(args.path).resolve() if args.path else _default_config_path(vault_root)
    cfg = _load_config(config_path)
    payload = {"kind": "algotrading_config_show", "path": str(config_path), "ok": bool(cfg), "config": cfg}
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["path", str(config_path)])
        _print_tab(["ok", int(bool(cfg))])
        if cfg:
            keys = sorted(cfg.keys())
            _print_tab(["keys", ",".join(keys)])
    return 0 if cfg else 1


def _cmd_algotrading_config_validate(args: argparse.Namespace) -> int:
    vault_root = Path(args.vault_root).resolve()
    config_path = Path(args.path).resolve() if args.path else _default_config_path(vault_root)
    cfg = _load_config(config_path)
    errors: list[str] = []
    if not cfg:
        errors.append("config_missing_or_invalid_json")
    else:
        for key in ["vault_root", "assistant_root", "env"]:
            if key not in cfg:
                errors.append(f"missing:{key}")
        if "env" in cfg and not isinstance(cfg.get("env"), dict):
            errors.append("invalid:env_not_object")
    payload = {"kind": "algotrading_config_validate", "path": str(config_path), "errors": errors}
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["path", str(config_path)])
        _print_tab(["errors", len(errors)])
        for e in errors:
            _print_tab(["error", e])
    return 1 if errors else 0


def _cmd_algotrading_run(args: argparse.Namespace) -> int:
    assistant_root = Path(args.assistant_root).resolve()
    python_cmd = _resolve_python_command(assistant_root)
    if not python_cmd:
        print("python not found", file=sys.stderr)
        return 2

    config_path: Path | None = None
    if args.config:
        config_path = Path(args.config).resolve()
    else:
        vault_root = Path(getattr(args, "vault_root", _default_vault_algotrading_root())).resolve()
        default_cfg = _default_config_path(vault_root)
        if default_cfg.exists():
            config_path = default_cfg

    env: dict[str, str] = {}
    if config_path:
        cfg = _load_config(config_path)
        env.update(_config_env(cfg))
    if args.env_file:
        env.update(_env_from_file(Path(args.env_file).resolve()))
    for item in list(args.env or []):
        raw = str(item)
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        if not k:
            continue
        env[k] = v.strip()

    base = str(args.base or "").strip()
    out = str(args.out or "").strip()
    if config_path:
        cfg = _load_config(config_path)
        if not base:
            base = str(cfg.get("base_dir", "") or "").strip()
        if not out:
            out = str(cfg.get("out_dir", "") or "").strip()
    limit = int(args.limit)
    if not base:
        print("--base is required (or set base_dir in config)", file=sys.stderr)
        return 2

    code, stdout, stderr = _run_python(
        python_cmd,
        assistant_root,
        ["scripts/run_algo.py", "--base", base, "--out", out, "--limit", str(limit)],
        extra_env=env,
    )

    payload = {
        "kind": "algotrading_run",
        "assistant_root": str(assistant_root),
        "config_path": str(config_path) if config_path else "",
        "code": int(code),
        "env_keys": sorted(env.keys()),
        "stdout": stdout[-20000:],
        "stderr": stderr[-20000:],
    }

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["code", int(code)])
        _print_tab(["assistant_root", str(assistant_root)])
        if env:
            _print_tab(["env_keys", ",".join(sorted(env.keys()))])
        if stdout.strip():
            print(stdout, end="")
        if stderr.strip():
            print(stderr, file=sys.stderr, end="")

    return int(code)


def _cmd_algotrading_optimize_lessons(args: argparse.Namespace) -> int:
    assistant_root = Path(args.assistant_root).resolve()
    python_cmd = _resolve_python_command(assistant_root)
    if not python_cmd:
        print("python not found", file=sys.stderr)
        return 2

    env: dict[str, str] = {}
    cfg: dict[str, object] = {}
    if args.config:
        cfg = _load_config(Path(args.config).resolve())
        env.update(_config_env(cfg))
    if args.env_file:
        env.update(_env_from_file(Path(args.env_file).resolve()))
    for item in list(args.env or []):
        raw = str(item)
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        if not k:
            continue
        env[k] = v.strip()

    argv = ["scripts/optimize_lessons.py"]
    raw_lessons = cfg.get("optimize_lessons")
    lessons_cfg: dict[str, object] = raw_lessons if isinstance(raw_lessons, dict) else {}
    source = args.source or lessons_cfg.get("source")
    output = args.output or lessons_cfg.get("output")
    reports = args.reports or lessons_cfg.get("reports")
    if source:
        argv += ["--source", str(source)]
    if output:
        argv += ["--output", str(output)]
    if reports:
        argv += ["--reports", str(reports)]
    if bool(args.write_versions) or bool(lessons_cfg.get("write_versions", False)):
        argv.append("--write-versions")
    if bool(args.no_index) or bool(lessons_cfg.get("no_index", False)):
        argv.append("--no-index")

    code, stdout, stderr = _run_python(python_cmd, assistant_root, argv, extra_env=env)

    payload = {
        "kind": "algotrading_optimize_lessons",
        "assistant_root": str(assistant_root),
        "code": int(code),
        "env_keys": sorted(env.keys()),
        "stdout": stdout[-20000:],
        "stderr": stderr[-20000:],
    }
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["code", int(code)])
        if stdout.strip():
            print(stdout, end="")
        if stderr.strip():
            print(stderr, file=sys.stderr, end="")
    return int(code)


def _cmd_algotrading_media_db_migrate(args: argparse.Namespace) -> int:
    assistant_root = Path(args.assistant_root).resolve()
    python_cmd = _resolve_python_command(assistant_root)
    if not python_cmd:
        print("python not found", file=sys.stderr)
        return 2

    env: dict[str, str] = {}
    cfg: dict[str, object] = {}
    if args.config:
        cfg = _load_config(Path(args.config).resolve())
        env.update(_config_env(cfg))
    if args.env_file:
        env.update(_env_from_file(Path(args.env_file).resolve()))
    for item in list(args.env or []):
        raw = str(item)
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        if not k:
            continue
        env[k] = v.strip()

    argv = ["scripts/media_db_migrate.py"]
    raw_mig = cfg.get("media_db_migrate")
    mig_cfg: dict[str, object] = raw_mig if isinstance(raw_mig, dict) else {}

    source = args.source or mig_cfg.get("source")
    target = args.target or mig_cfg.get("target")
    report_dir = args.report_dir or mig_cfg.get("report_dir")
    stage = args.stage or mig_cfg.get("stage")
    dedup_mode = args.dedup_mode or mig_cfg.get("dedup_mode")
    backup_mode = args.backup_mode or mig_cfg.get("backup_mode")
    backup_dir = args.backup_dir or mig_cfg.get("backup_dir")

    if source:
        argv += ["--source", str(source)]
    if target:
        argv += ["--target", str(target)]
    if report_dir:
        argv += ["--report-dir", str(report_dir)]
    if stage:
        argv += ["--stage", str(stage)]
    if bool(args.approve_dedup) or bool(mig_cfg.get("approve_dedup", False)):
        argv.append("--approve-dedup")
    if dedup_mode:
        argv += ["--dedup-mode", str(dedup_mode)]
    if backup_mode:
        argv += ["--backup-mode", str(backup_mode)]
    if backup_dir:
        argv += ["--backup-dir", str(backup_dir)]
    if bool(args.dry_run) or bool(mig_cfg.get("dry_run", False)):
        argv.append("--dry-run")
    if bool(args.move) or bool(mig_cfg.get("move", False)):
        argv.append("--move")

    code, stdout, stderr = _run_python(python_cmd, assistant_root, argv, extra_env=env)
    payload = {
        "kind": "algotrading_media_db_migrate",
        "assistant_root": str(assistant_root),
        "code": int(code),
        "env_keys": sorted(env.keys()),
        "stdout": stdout[-20000:],
        "stderr": stderr[-20000:],
    }
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["code", int(code)])
        if stdout.strip():
            print(stdout, end="")
        if stderr.strip():
            print(stderr, file=sys.stderr, end="")
    return int(code)


def add_algotrading_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    algo = sub.add_parser("algotrading")
    algo_sub = algo.add_subparsers(dest="algotrading_cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--assistant-root", default=str(_default_assistant_root()))
        p.add_argument("--vault-root", default=str(_default_vault_algotrading_root()))

    doctor = algo_sub.add_parser("doctor")
    add_common(doctor)
    doctor.add_argument("--config", default=None)
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=_cmd_algotrading_doctor)

    sync = algo_sub.add_parser("sync-ssot")
    add_common(sync)
    sync.add_argument("--force", action="store_true")
    sync.add_argument("--json", action="store_true")
    sync.set_defaults(func=_cmd_algotrading_sync_ssot)

    cfgp = algo_sub.add_parser("config")
    cfg_sub = cfgp.add_subparsers(dest="config_cmd", required=True)

    cfg_init = cfg_sub.add_parser("init")
    cfg_init.add_argument("--vault-root", default=str(_default_vault_algotrading_root()))
    cfg_init.add_argument("--path", default=None)
    cfg_init.add_argument("--fill-from-vault", action="store_true")
    cfg_init.add_argument("--force", action="store_true")
    cfg_init.add_argument("--json", action="store_true")
    cfg_init.set_defaults(func=_cmd_algotrading_config_init)

    cfg_show = cfg_sub.add_parser("show")
    cfg_show.add_argument("--vault-root", default=str(_default_vault_algotrading_root()))
    cfg_show.add_argument("--path", default=None)
    cfg_show.add_argument("--json", action="store_true")
    cfg_show.set_defaults(func=_cmd_algotrading_config_show)

    cfg_val = cfg_sub.add_parser("validate")
    cfg_val.add_argument("--vault-root", default=str(_default_vault_algotrading_root()))
    cfg_val.add_argument("--path", default=None)
    cfg_val.add_argument("--json", action="store_true")
    cfg_val.set_defaults(func=_cmd_algotrading_config_validate)

    runp = algo_sub.add_parser("run")
    runp.add_argument("--assistant-root", default=str(_default_assistant_root()))
    runp.add_argument("--vault-root", default=str(_default_vault_algotrading_root()))
    runp.add_argument("--config", default=None)
    runp.add_argument("--base", default=None)
    runp.add_argument("--out", default=None)
    runp.add_argument("--limit", type=int, default=0)
    runp.add_argument("--env-file", default=None)
    runp.add_argument("--env", nargs="*", default=[])
    runp.add_argument("--json", action="store_true")
    runp.set_defaults(func=_cmd_algotrading_run)

    opt = algo_sub.add_parser("optimize-lessons")
    opt.add_argument("--assistant-root", default=str(_default_assistant_root()))
    opt.add_argument("--config", default=None)
    opt.add_argument("--source", default=None)
    opt.add_argument("--output", default=None)
    opt.add_argument("--reports", default=None)
    opt.add_argument("--write-versions", action="store_true")
    opt.add_argument("--no-index", action="store_true")
    opt.add_argument("--env-file", default=None)
    opt.add_argument("--env", nargs="*", default=[])
    opt.add_argument("--json", action="store_true")
    opt.set_defaults(func=_cmd_algotrading_optimize_lessons)

    mig = algo_sub.add_parser("media-db-migrate")
    mig.add_argument("--assistant-root", default=str(_default_assistant_root()))
    mig.add_argument("--config", default=None)
    mig.add_argument("--source", default=None)
    mig.add_argument("--target", default=None)
    mig.add_argument("--report-dir", default=None)
    mig.add_argument("--stage", default="all")
    mig.add_argument("--approve-dedup", action="store_true")
    mig.add_argument("--dedup-mode", default=None)
    mig.add_argument("--backup-mode", default=None)
    mig.add_argument("--backup-dir", default=None)
    mig.add_argument("--dry-run", action="store_true")
    mig.add_argument("--move", action="store_true")
    mig.add_argument("--env-file", default=None)
    mig.add_argument("--env", nargs="*", default=[])
    mig.add_argument("--json", action="store_true")
    mig.set_defaults(func=_cmd_algotrading_media_db_migrate)
