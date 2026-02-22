import json
import shutil
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from run_ops import _node_package_manager, _read_package_json_scripts, _resolve_pytest_command, _resolve_python_command, plan_preset_commands


def _tmp_dir(name: str) -> Path:
    root = Path(__file__).resolve().parent / f".tmp_run_ops_{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


class RunOpsTest(unittest.TestCase):
    def tearDown(self) -> None:
        parent = Path(__file__).resolve().parent
        for path in parent.glob(".tmp_run_ops_*"):
            shutil.rmtree(path, ignore_errors=True)

    def test_python_test_uses_pytest_exe_when_present(self) -> None:
        root = _tmp_dir("pytest")
        (root / "pyproject.toml").write_text("", encoding="utf-8")
        py = root / "env312" / "Scripts" / "python.exe"
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_text("", encoding="utf-8")
        (py.parent / "pytest.exe").write_text("", encoding="utf-8")

        plan = plan_preset_commands(root, "test")
        self.assertEqual(plan, [[str(py.parent / "pytest.exe"), "-q"]])

    def test_python_test_falls_back_to_unittest(self) -> None:
        root = _tmp_dir("unittest")
        (root / "pyproject.toml").write_text("", encoding="utf-8")
        (root / "tests").mkdir()
        py = root / "env312" / "Scripts" / "python.exe"
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_text("", encoding="utf-8")

        plan = plan_preset_commands(root, "test")
        self.assertEqual(
            plan,
            [[str(py), "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-q"]],
        )

    def test_python_lint_requires_ruff_config(self) -> None:
        root = _tmp_dir("ruff")
        (root / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value="ruff"):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [["ruff", "check", "."]])

    def test_python_lint_uses_python_module_when_ruff_not_in_path(self) -> None:
        root = _tmp_dir("ruff_mod")
        (root / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
        py = root / "env312" / "Scripts" / "python.exe"
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_text("", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value=None):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [[str(py), "-m", "ruff", "check", "."]])

    def test_node_lint_uses_package_manager(self) -> None:
        root = _tmp_dir("node")
        (root / "package.json").write_text(json.dumps({"scripts": {"lint": "echo ok"}}), encoding="utf-8")
        (root / "package-lock.json").write_text("{}", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value="npm"):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [["npm", "run", "lint"]])

    def test_node_missing_script_returns_empty(self) -> None:
        root = _tmp_dir("node_missing")
        (root / "package.json").write_text(json.dumps({"scripts": {"test": "echo ok"}}), encoding="utf-8")
        (root / "package-lock.json").write_text("{}", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value="npm"):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [])

    def test_node_invalid_package_json_returns_empty(self) -> None:
        root = _tmp_dir("node_invalid")
        (root / "package.json").write_text("{", encoding="utf-8")
        (root / "package-lock.json").write_text("{}", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value="npm"):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [])

    def test_go_presets_planned(self) -> None:
        root = _tmp_dir("go")
        (root / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")

        self.assertEqual(plan_preset_commands(root, "test"), [["go", "test", "./..."]])
        self.assertEqual(plan_preset_commands(root, "build"), [["go", "build", "./..."]])
        self.assertEqual(plan_preset_commands(root, "lint"), [["gofmt", "-l", "."]])

    def test_rust_lint_includes_fmt_and_clippy_when_cargo_present(self) -> None:
        root = _tmp_dir("rust_lint")
        (root / "Cargo.toml").write_text("", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", side_effect=lambda name: "cargo" if name == "cargo" else None):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [["cargo", "fmt", "--", "--check"], ["cargo", "clippy", "--", "-D", "warnings"]])

    def test_rust_lint_empty_without_cargo(self) -> None:
        root = _tmp_dir("rust")
        (root / "Cargo.toml").write_text("", encoding="utf-8")

        def which(name: str) -> str | None:
            if name == "cargo":
                return None
            return shutil.which(name)

        with mock.patch("run_ops.shutil.which", side_effect=which):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [])

    def test_resolve_python_command_skips_windows_store_alias(self) -> None:
        root = _tmp_dir("py_alias")
        store_alias = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"
        python3 = r"C:\Python\python3.exe"

        with (
            mock.patch("run_ops.Path.exists", return_value=False),
            mock.patch(
                "run_ops.shutil.which",
                side_effect=lambda name: store_alias if name == "python" else (python3 if name == "python3" else None),
            ),
        ):
            resolved = _resolve_python_command(root)

        self.assertEqual(resolved, python3)

    def test_resolve_pytest_command_falls_back_to_path(self) -> None:
        root = _tmp_dir("pytest_path")
        with mock.patch("run_ops.shutil.which", return_value="pytest"):
            cmd = _resolve_pytest_command(root, python_cmd=None)
        self.assertEqual(cmd, ["pytest", "-q"])

    def test_node_package_manager_prefers_pnpm_when_lock_present(self) -> None:
        root = _tmp_dir("pnpm")
        (root / "pnpm-lock.yaml").write_text("", encoding="utf-8")

        def which(name: str) -> str | None:
            if name == "pnpm":
                return "pnpm"
            if name == "npm":
                return "npm"
            return None

        with mock.patch("run_ops.shutil.which", side_effect=which):
            mgr = _node_package_manager(root)
        self.assertEqual(mgr, "pnpm")

    def test_read_package_json_scripts_requires_dict(self) -> None:
        root = _tmp_dir("pkg_scripts")
        (root / "package.json").write_text(json.dumps({"scripts": ["x"]}), encoding="utf-8")
        scripts = _read_package_json_scripts(root)
        self.assertEqual(scripts, {})

    def test_resolve_python_command_returns_none_when_no_candidates(self) -> None:
        root = _tmp_dir("py_none")

        with (
            mock.patch("run_ops.Path.exists", return_value=False),
            mock.patch("run_ops.shutil.which", return_value=None),
        ):
            resolved = _resolve_python_command(root)

        self.assertIsNone(resolved)

    def test_node_package_manager_falls_back_to_npm_when_available(self) -> None:
        root = _tmp_dir("npm_fallback")

        def which(name: str) -> str | None:
            if name == "npm":
                return "npm"
            return None

        with mock.patch("run_ops.shutil.which", side_effect=which):
            mgr = _node_package_manager(root)
        self.assertEqual(mgr, "npm")

    def test_resolve_python_command_returns_system_python_when_found(self) -> None:
        root = _tmp_dir("py_sys")
        sys_py = r"C:\Python\python.exe"

        with (
            mock.patch("run_ops.Path.exists", return_value=False),
            mock.patch("run_ops.shutil.which", side_effect=lambda name: sys_py if name == "python" else None),
        ):
            resolved = _resolve_python_command(root)

        self.assertEqual(resolved, sys_py)

    def test_resolve_pytest_command_uses_adjacent_pytest_on_non_exe(self) -> None:
        root = _tmp_dir("pytest_nonexe")
        bin_dir = root / "venv" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        py = bin_dir / "python"
        py.write_text("", encoding="utf-8")
        (bin_dir / "pytest").write_text("", encoding="utf-8")

        cmd = _resolve_pytest_command(root, python_cmd=str(py))
        self.assertEqual(cmd, [str(bin_dir / "pytest"), "-q"])

    def test_node_package_manager_uses_yarn_when_lock_present(self) -> None:
        root = _tmp_dir("yarn")
        (root / "yarn.lock").write_text("", encoding="utf-8")

        def which(name: str) -> str | None:
            if name == "yarn":
                return "yarn"
            if name == "npm":
                return "npm"
            return None

        with mock.patch("run_ops.shutil.which", side_effect=which):
            mgr = _node_package_manager(root)
        self.assertEqual(mgr, "yarn")

    def test_read_package_json_scripts_empty_file_returns_empty(self) -> None:
        root = _tmp_dir("pkg_empty")
        (root / "package.json").write_text("", encoding="utf-8")
        scripts = _read_package_json_scripts(root)
        self.assertEqual(scripts, {})

    def test_plan_preset_commands_node_requires_manager(self) -> None:
        root = _tmp_dir("node_nomgr")
        (root / "package.json").write_text(json.dumps({"scripts": {"lint": "x"}}), encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value=None):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [])

    def test_plan_preset_commands_python_test_returns_empty_without_python(self) -> None:
        root = _tmp_dir("py_no_python")
        (root / "pyproject.toml").write_text("", encoding="utf-8")
        (root / "tests").mkdir()

        with (
            mock.patch("run_ops._resolve_python_command", return_value=None),
            mock.patch("run_ops._resolve_pytest_command", return_value=None),
        ):
            plan = plan_preset_commands(root, "test")

        self.assertEqual(plan, [])

    def test_plan_preset_commands_python_lint_returns_empty_without_config(self) -> None:
        root = _tmp_dir("py_no_cfg")
        (root / "pyproject.toml").write_text("", encoding="utf-8")

        with mock.patch("run_ops.shutil.which", return_value="ruff"):
            plan = plan_preset_commands(root, "lint")

        self.assertEqual(plan, [])

    def test_plan_preset_commands_rust_test_and_build(self) -> None:
        root = _tmp_dir("rust_tb")
        (root / "Cargo.toml").write_text("", encoding="utf-8")
        self.assertEqual(plan_preset_commands(root, "test"), [["cargo", "test"]])
        self.assertEqual(plan_preset_commands(root, "build"), [["cargo", "build"]])
