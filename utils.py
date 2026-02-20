from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence, TextIO, TypeVar


def _print_json(payload: Mapping[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _print_tab(fields: Sequence[object]) -> None:
    print("\t".join(str(field) for field in fields))


def _print_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


_T = TypeVar("_T")


def _apply_limit(items: list[_T], limit: int | None) -> list[_T]:
    if limit is None:
        return items
    return items[: max(0, int(limit))]


def _ensure_dir_exists(path: Path, label: str) -> bool:
    if path.exists():
        return True
    print(f"{label} not found: {path}", file=sys.stderr)
    return False


def _ensure_file_exists(path: Path, label: str) -> bool:
    if path.exists():
        return True
    print(f"{label} not found: {path}", file=sys.stderr)
    return False


def _load_global_gitignore() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    path = root / ".trae" / "global_gitignore_localai"
    text = _read_text(path)
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def _read_gitignore_lines(path: Path) -> list[str]:
    text = _read_text(path)
    if not text:
        return []
    return [ln.rstrip("\n") for ln in text.splitlines()]


def _apply_gitignore_lines(
    gitignore_path: Path,
    entries: list[str],
    dry_run: bool,
) -> tuple[bool, list[str], str | None]:
    existing = _read_gitignore_lines(gitignore_path)
    existing_set = {ln for ln in existing if ln}
    missing = [ln for ln in entries if ln and ln not in existing_set]
    if not missing:
        return False, [], None
    if dry_run:
        return True, missing, None
    try:
        if existing:
            text = "\n".join(existing).rstrip("\n") + "\n" + "\n".join(missing) + "\n"
        else:
            text = "\n".join(missing) + "\n"
        _write_text_atomic(gitignore_path, text, backup=True)
    except OSError as exc:
        return False, missing, str(exc)
    return True, missing, None


def _run_command(cmd: Sequence[str], cwd: Path) -> int:
    argv = list(cmd)
    if not argv:
        return 0
    try:
        completed = subprocess.run(argv, cwd=str(cwd))
    except FileNotFoundError:
        print(f"tool not found: {argv[0]}", file=sys.stderr)
        return 127
    return int(completed.returncode)


def _run_capture(cmd: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    argv = list(cmd)
    if not argv:
        return 0, "", ""
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return 127, "", f"tool not found: {argv[0]}"
    except OSError as exc:
        return 1, "", str(exc)
    return int(completed.returncode), completed.stdout, completed.stderr


def _write_stream(stream: TextIO, text: str) -> None:
    if not text:
        return
    stream.write(text)
    if not text.endswith("\n"):
        stream.write("\n")
    stream.flush()


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _write_text_atomic(path: Path, text: str, backup: bool = False) -> None:
    tmp = path.with_name(f"{path.name}.tmp_{os.getpid()}_{int(time.time() * 1000)}")
    tmp.write_text(text, encoding="utf-8")
    if backup and path.exists():
        bak = path.with_name(f"{path.name}.bak")
        try:
            if bak.exists():
                bak.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            path.replace(bak)
        except OSError:
            pass
    tmp.replace(path)


def _read_json_object(path: Path) -> dict[str, object] | None:
    text = _read_text(path)
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _safe_file_count(path: Path, pattern: str) -> int:
    if not path.is_dir():
        return 0
    try:
        return sum(1 for item in path.glob(pattern) if item.is_file())
    except PermissionError:
        return 0


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _path_exists_from_value(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        return Path(value).exists()
    except OSError:
        return False
