import io
import json
import shutil
import subprocess
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock
from uuid import uuid4

from integrator.app import GitStatus, iter_projects, plan_preset_commands, run


@contextmanager
def project_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_case_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class ProjectsTest(unittest.TestCase):
    def test_iter_projects_finds_marker_files(self) -> None:
        with project_case_dir() as root:
            a = root / "a"
            a.mkdir()
            (a / "pyproject.toml").write_text("", encoding="utf-8")

            b = root / "b"
            b.mkdir()
            (b / ".git").mkdir()

            c = root / "c"
            c.mkdir()

            projects = iter_projects([root], max_depth=1)
            names = {p.name for p in projects}
            self.assertEqual(names, {"a", "b"})

    def test_iter_projects_finds_agent_workflow_dirs(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            projects = iter_projects([root], max_depth=3)
            names = {p.name for p in projects}
            self.assertIn("agent_gateway", names)

    def test_doctor_runs(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run(["integrator", "doctor"])
        self.assertEqual(code, 0)
        self.assertIn("python=", buf.getvalue())

    def test_diagnostics_only_problems(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run(["integrator", "diagnostics", "--only-problems", "--json"])
        self.assertIn(code, {0, 1})
        lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        for line in lines:
            obj = json.loads(line)
            self.assertNotEqual(obj["status"], "ok")

    def test_projects_list_strict_roots_reports_missing(self) -> None:
        missing = Path(__file__).resolve().parent / ".tmp_missing_root"
        if missing.exists():
            shutil.rmtree(missing, ignore_errors=True)
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            code = run(
                [
                    "integrator",
                    "projects",
                    "list",
                    "--roots",
                    str(missing),
                    "--strict-roots",
                    "--max-depth",
                    "1",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("status=missing", err_buf.getvalue())

    def test_status_strict_roots_reports_access_denied(self) -> None:
        with project_case_dir() as root:
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with mock.patch("integrator.cli._root_status", return_value="access_denied"):
                with redirect_stdout(out_buf), redirect_stderr(err_buf):
                    code = run(
                        [
                            "integrator",
                            "status",
                            "--roots",
                            str(root),
                            "--strict-roots",
                            "--max-depth",
                            "1",
                        ]
                    )
            self.assertEqual(code, 2)
            self.assertIn("status=access_denied", err_buf.getvalue())

    def test_status_reports_git_repo(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "status",
                        "--roots",
                        str(root),
                        "--max-depth",
                        "1",
                    ]
                )
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("repo", out)
            self.assertIn("\tclean\t", out)

    def test_status_json_is_parseable(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "status",
                        "--json",
                        "--roots",
                        str(root),
                        "--max-depth",
                        "1",
                    ]
                )
            self.assertEqual(code, 0)
            line = buf.getvalue().strip().splitlines()[0]
            obj = json.loads(line)
            self.assertEqual(obj["name"], "repo")
            self.assertEqual(obj["state"], "clean")

    def test_remotes_only_github_normalizes(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "git@github.com:egork/test.git"],
                cwd=str(repo),
                check=True,
                capture_output=True,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "remotes",
                        "--only-github",
                        "--roots",
                        str(root),
                        "--max-depth",
                        "1",
                    ]
                )
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("https://github.com/egork/test", out)

    def test_git_bootstrap_ignore_adds_missing(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            (repo / "pyproject.toml").write_text("", encoding="utf-8")
            (repo / ".git").mkdir()
            (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

            with mock.patch("integrator.utils._load_global_gitignore", return_value=["cache/", "logs/"]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "git",
                            "bootstrap-ignore",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "1",
                        ]
                    )
            self.assertEqual(code, 0)
            lines = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
            self.assertIn("node_modules/", lines)
            self.assertIn("cache/", lines)
            self.assertIn("logs/", lines)

    def test_run_dry_run_json_prints_commands(self) -> None:
        with project_case_dir() as project:
            (project / "pyproject.toml").write_text("", encoding="utf-8")
            (project / "tests").mkdir()

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "run", "test", "--cwd", str(project), "--dry-run", "--json"])
            self.assertEqual(code, 0)
            obj = json.loads(buf.getvalue().strip().splitlines()[0])
            self.assertEqual(obj["preset"], "test")
            self.assertTrue(obj["commands"])

    def test_run_require_clean_blocks_dirty_projects(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            (repo / "pyproject.toml").write_text("", encoding="utf-8")
            (repo / "tests").mkdir()
            (repo / ".git").mkdir()

            dirty = GitStatus(
                branch="main",
                upstream="",
                ahead=0,
                behind=0,
                clean=False,
                changed=1,
                untracked=1,
                raw=" M file",
            )

            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with mock.patch("integrator.git_ops._git_status", return_value=dirty):
                with redirect_stdout(out_buf), redirect_stderr(err_buf):
                    code = run(
                        [
                            "integrator",
                            "run",
                            "test",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "1",
                            "--require-clean",
                            "--dry-run",
                        ]
                    )
            self.assertEqual(code, 2)
            self.assertIn("preflight_dirty", err_buf.getvalue())

    def test_plan_preset_commands_python_unittest(self) -> None:
        with project_case_dir() as project:
            (project / "pyproject.toml").write_text("", encoding="utf-8")
            (project / "tests").mkdir()

            with mock.patch("integrator.run_ops._resolve_pytest_command", return_value=None):
                cmds = plan_preset_commands(project, "test")
            self.assertTrue(cmds)
            self.assertEqual(
                cmds[0][1:4],
                ["-m", "unittest", "discover"],
            )

    def test_localai_list_uses_custom_root(self) -> None:
        with project_case_dir() as root:
            a = root / "assistant"
            a.mkdir()
            (a / ".git").mkdir()

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "localai", "list", "--root", str(root), "--max-depth", "1"])
            self.assertEqual(code, 0)
            self.assertIn("assistant", buf.getvalue())

    def test_projects_info_json_has_kind(self) -> None:
        with project_case_dir() as root:
            nodep = root / "nodep"
            nodep.mkdir()
            (nodep / "package.json").write_text('{"name":"nodep"}', encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "projects", "info", "--json", "--roots", str(root), "--max-depth", "1"])
            self.assertEqual(code, 0)
            obj = json.loads(buf.getvalue().strip().splitlines()[0])
            self.assertEqual(obj["name"], "nodep")
            self.assertEqual(obj["kind"], "node")

    def test_projects_info_json_kind_agent(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "projects", "info", "--json", "--roots", str(root), "--max-depth", "3"])
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            row = next(item for item in rows if item["name"] == "agent_gateway")
            self.assertEqual(row["kind"], "agent")

    def test_projects_list_limit_and_filter(self) -> None:
        with project_case_dir() as root:
            a = root / "aaa"
            a.mkdir()
            (a / "pyproject.toml").write_text("", encoding="utf-8")
            b = root / "bbb"
            b.mkdir()
            (b / "pyproject.toml").write_text("", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "projects",
                        "list",
                        "--roots",
                        str(root),
                        "--max-depth",
                        "1",
                        "--project",
                        "bbb",
                        "--limit",
                        "1",
                    ]
                )
            self.assertEqual(code, 0)
            lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith("bbb\t"))

    def test_report_json_includes_github(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "git@github.com:egork/test.git"],
                cwd=str(repo),
                check=True,
                capture_output=True,
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "report",
                        "--json",
                        "--roots",
                        str(root),
                        "--max-depth",
                        "1",
                    ]
                )
            self.assertEqual(code, 0)
            obj = json.loads(buf.getvalue().strip().splitlines()[0])
            self.assertEqual(obj["name"], "repo")
            self.assertEqual(obj["github"], "https://github.com/egork/test")

    def test_agents_list_json_has_types(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            media = root / "projects" / "media_storage"
            (media / "config").mkdir(parents=True)
            (media / "scripts").mkdir()
            (media / "config" / "media_paths.json").write_text(
                '{"media_root":"C:/A","work_root":"C:/B","publish_root":"C:/C"}',
                encoding="utf-8",
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "agents", "list", "--json", "--roots", str(root), "--max-depth", "3"])
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            types = {row["name"]: row["agent_type"] for row in rows}
            self.assertEqual(types["agent_gateway"], "gateway")
            self.assertEqual(types["media_storage"], "media-storage")

    def test_agents_status_json_reports_gateway_up(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            with mock.patch("integrator.agents_ops._is_endpoint_up", return_value=True):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "agents",
                            "status",
                            "--json",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "3",
                        ]
                    )
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            row = next(item for item in rows if item["name"] == "agent_gateway")
            self.assertTrue(row["gateway_up"])
            self.assertEqual(row["agent_type"], "gateway")
            self.assertEqual(row["problems"], [])

    def test_agents_status_only_problems_filters_healthy(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            with mock.patch("integrator.agents_ops._is_endpoint_up", return_value=True):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "agents",
                            "status",
                            "--json",
                            "--only-problems",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "3",
                        ]
                    )
            self.assertEqual(code, 0)
            lines = [line for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(lines, [])

    def test_agents_status_only_problems_finds_gateway_down(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            with mock.patch("integrator.agents_ops._is_endpoint_up", return_value=False):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "agents",
                            "status",
                            "--json",
                            "--only-problems",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "3",
                        ]
                    )
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "agent_gateway")
            self.assertIn("gateway_unreachable", rows[0]["problems"])

    def test_agents_status_fix_hints_includes_gateway_check(self) -> None:
        with project_case_dir() as root:
            gateway = root / "projects" / "agent_gateway"
            (gateway / "config").mkdir(parents=True)
            (gateway / "scripts").mkdir()
            (gateway / "config" / "gateway.json").write_text(
                '{"base_url":"http://127.0.0.1:8011","routes":{"memory_write":"/agent/memory/write"}}',
                encoding="utf-8",
            )

            with mock.patch("integrator.agents_ops._is_endpoint_up", return_value=False):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "agents",
                            "status",
                            "--json",
                            "--only-problems",
                            "--fix-hints",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "3",
                        ]
                    )
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            hints = rows[0].get("fix_hints", [])
            self.assertIn("Test-NetConnection 127.0.0.1 -Port 8011", hints)

    def test_status_json_reports_tool_missing(self) -> None:
        with project_case_dir() as root:
            repo = root / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()

            buf = io.StringIO()
            with mock.patch("integrator.utils._run_capture", return_value=(127, "", "tool not found: git")):
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "status",
                            "--json",
                            "--roots",
                            str(root),
                            "--max-depth",
                            "1",
                        ]
                    )
            self.assertEqual(code, 1)
            obj = json.loads(buf.getvalue().strip().splitlines()[0])
            self.assertEqual(obj["state"], "tool-missing")

    def test_run_json_strict_keeps_stdout_jsonl(self) -> None:
        with project_case_dir() as project:
            (project / "pyproject.toml").write_text("", encoding="utf-8")
            (project / "tests").mkdir()

            out_buf = io.StringIO()
            err_buf = io.StringIO()

            def fake_run_capture(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
                if len(cmd) >= 3 and cmd[1:3] == ["-m", "unittest"]:
                    return 0, "child stdout\n", "child stderr\n"
                return 0, "", ""

            with mock.patch("integrator.cli._run_capture", side_effect=fake_run_capture):
                with redirect_stdout(out_buf), redirect_stderr(err_buf):
                    code = run(
                        [
                            "integrator",
                            "run",
                            "test",
                            "--cwd",
                            str(project),
                            "--json",
                            "--json-strict",
                        ]
                    )

            self.assertEqual(code, 0)
            lines = [ln for ln in out_buf.getvalue().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["dry_run"], False)
            self.assertIn("child stdout", err_buf.getvalue())
            self.assertIn("child stderr", err_buf.getvalue())

    def test_run_json_strict_requires_json(self) -> None:
        with project_case_dir() as project:
            (project / "pyproject.toml").write_text("", encoding="utf-8")
            (project / "tests").mkdir()

            err_buf = io.StringIO()
            with redirect_stderr(err_buf):
                code = run(
                    [
                        "integrator",
                        "run",
                        "test",
                        "--cwd",
                        str(project),
                        "--json-strict",
                        "--dry-run",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("--json-strict requires --json", err_buf.getvalue())
