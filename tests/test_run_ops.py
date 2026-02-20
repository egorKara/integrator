import json
import shutil
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from run_ops import plan_preset_commands


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
