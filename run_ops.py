from __future__ import annotations

import json
import shutil
from pathlib import Path

from scan import _project_kind
from utils import _read_text


def _resolve_python_command(project_dir: Path) -> str | None:
    def is_windows_store_alias(path: str) -> bool:
        normalized = path.replace("/", "\\").lower()
        return "\\microsoft\\windowsapps\\python.exe" in normalized

    candidates = [
        project_dir / "env312" / "Scripts" / "python.exe",
        project_dir / ".venv" / "Scripts" / "python.exe",
        project_dir / "venv" / "Scripts" / "python.exe",
        project_dir / ".venv" / "bin" / "python",
        project_dir / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    import sys

    if Path(sys.executable).exists():
        return sys.executable

    system_python = shutil.which("python")
    if system_python and not is_windows_store_alias(system_python):
        return system_python

    python3 = shutil.which("python3")
    if python3 and not is_windows_store_alias(python3):
        return python3

    return None


def _resolve_pytest_command(project_dir: Path, python_cmd: str | None) -> list[str] | None:
    if python_cmd:
        python_path = Path(python_cmd)
        if python_path.is_absolute() and python_path.name.lower().startswith("python"):
            if python_path.suffix.lower() == ".exe":
                pytest_candidate = python_path.with_name("pytest.exe")
            else:
                pytest_candidate = python_path.with_name("pytest")
            if pytest_candidate.exists():
                return [str(pytest_candidate), "-q"]

    pytest_bin = shutil.which("pytest")
    if pytest_bin:
        return [pytest_bin, "-q"]
    return None


def _node_package_manager(project_dir: Path) -> str | None:
    if (project_dir / "package-lock.json").exists() and shutil.which("npm"):
        return "npm"
    if (project_dir / "pnpm-lock.yaml").exists() and shutil.which("pnpm"):
        return "pnpm"
    if (project_dir / "yarn.lock").exists() and shutil.which("yarn"):
        return "yarn"
    if shutil.which("npm"):
        return "npm"
    return None


def _read_package_json_scripts(project_dir: Path) -> dict[str, str]:
    package_json = project_dir / "package.json"
    text = _read_text(package_json)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(k): str(v) for k, v in scripts.items()}


def plan_preset_commands(project_dir: Path, preset: str) -> list[list[str]]:
    preset = preset.lower()
    kind = _project_kind(project_dir)

    if kind == "node":
        manager = _node_package_manager(project_dir)
        if not manager:
            return []
        scripts = _read_package_json_scripts(project_dir)
        target = preset
        if target not in {"lint", "test", "build"}:
            return []
        if target not in scripts:
            return []
        return [[manager, "run", target]]

    if kind == "python":
        python_cmd = _resolve_python_command(project_dir)
        if preset == "test":
            pytest_cmd = _resolve_pytest_command(project_dir, python_cmd)
            if pytest_cmd:
                return [pytest_cmd]
            if python_cmd:
                return [[python_cmd, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-q"]]
            return []
        if preset == "lint":
            pyproject = project_dir / "pyproject.toml"
            ruff_toml = project_dir / "ruff.toml"
            dot_ruff_toml = project_dir / ".ruff.toml"
            has_ruff_cfg = (
                ruff_toml.exists()
                or dot_ruff_toml.exists()
                or ("[tool.ruff" in (_read_text(pyproject) or ""))
            )
            if has_ruff_cfg:
                ruff_bin = shutil.which("ruff")
                if ruff_bin:
                    return [[ruff_bin, "check", "."]]
                if python_cmd:
                    return [[python_cmd, "-m", "ruff", "check", "."]]
            return []
        if preset == "build":
            if (project_dir / "pyproject.toml").exists() and python_cmd:
                return [[python_cmd, "-m", "build"]]
            return []
        return []

    if kind == "go":
        if preset == "test":
            return [["go", "test", "./..."]]
        if preset == "build":
            return [["go", "build", "./..."]]
        if preset == "lint":
            return [["gofmt", "-l", "."]]
        return []

    if kind == "rust":
        if preset == "test":
            return [["cargo", "test"]]
        if preset == "build":
            return [["cargo", "build"]]
        if preset == "lint":
            cmds: list[list[str]] = []
            if shutil.which("cargo"):
                cmds.append(["cargo", "fmt", "--", "--check"])
                cmds.append(["cargo", "clippy", "--", "-D", "warnings"])
            return cmds
        return []

    return []
