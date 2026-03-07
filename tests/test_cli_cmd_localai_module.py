import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import cli_cmd_localai


def _ns(**kwargs: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "root": ".",
        "max_depth": 4,
        "project": None,
        "limit": 50,
        "cwd": None,
        "recipe": "",
        "gateway_json": None,
        "base_url": "",
        "content_file": "",
        "summary": "",
        "auth_token": "",
        "tags": [],
        "chunk_size": 8000,
        "kind": "event",
        "source": "",
        "author": "",
        "module": "",
        "json": False,
        "q": "",
        "filter_kind": "",
        "filter_module": "",
        "include_quarantined": False,
        "include_deleted": False,
        "min_importance": None,
        "min_trust": None,
        "max_age_sec": None,
        "id": None,
        "rating": None,
        "notes": "",
        "title": "",
        "prio": "p2",
        "owner": "",
        "next_step": "",
        "daemon": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class LocalAiCmdModuleTests(unittest.TestCase):
    def test_cmd_localai_list_prints_limited_projects(self) -> None:
        args = _ns(root=".", max_depth=3, project="abc", limit=1)
        with mock.patch("cli_cmd_localai._projects_from_root", return_value=[Path("a"), Path("b")]) as projects_mock:
            with mock.patch("cli_cmd_localai._print_project_list") as print_mock:
                code = cli_cmd_localai._cmd_localai_list(args)
        self.assertEqual(code, 0)
        self.assertTrue(projects_mock.called)
        printed = print_mock.call_args.args[0]
        self.assertEqual(len(printed), 1)

    def test_memory_write_non_json_error_status_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            content = Path(td) / "x.txt"
            content.write_text("hello", encoding="utf-8")
            args = _ns(
                recipe="memory-write",
                base_url="http://127.0.0.1:8011",
                content_file=str(content),
                json=False,
            )
            fake_results = [mock.Mock(status=500, json={"record": {"id": 12}})]
            out = io.StringIO()
            with mock.patch("cli.memory_write_file", return_value=fake_results):
                with redirect_stdout(out):
                    code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 1)
        self.assertIn("error", out.getvalue())
        self.assertIn("12", out.getvalue())

    def test_memory_write_requires_base_url(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            content = Path(td) / "x.txt"
            content.write_text("hello", encoding="utf-8")
            args = _ns(recipe="memory-write", content_file=str(content))
            err = io.StringIO()
            with redirect_stderr(err):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("base_url required", err.getvalue())

    def test_memory_write_missing_content_file_path(self) -> None:
        args = _ns(recipe="memory-write", base_url="http://127.0.0.1:8011", content_file="X:/missing/report.md")
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("content_file missing", err.getvalue())

    def test_memory_write_json_mixed_statuses_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            content = Path(td) / "x.txt"
            content.write_text("hello", encoding="utf-8")
            args = _ns(
                recipe="memory-write",
                base_url="http://127.0.0.1:8011",
                content_file=str(content),
                json=True,
            )
            fake_results = [
                mock.Mock(status=200, json={"record": {"id": 1}}),
                mock.Mock(status=500, json={"error": "boom"}),
            ]
            out = io.StringIO()
            with mock.patch("cli.memory_write_file", return_value=fake_results):
                with redirect_stdout(out):
                    code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 1)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertEqual(rows[0]["ok"], True)
        self.assertEqual(rows[1]["ok"], False)

    def test_memory_search_requires_query(self) -> None:
        args = _ns(recipe="memory-search", base_url="http://127.0.0.1:8011", q="")
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("q required", err.getvalue())

    def test_memory_feedback_requires_id_and_rating(self) -> None:
        args = _ns(recipe="memory-feedback", base_url="http://127.0.0.1:8011")
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("id and rating required", err.getvalue())

    def test_memory_recent_json_results_list_prints_records(self) -> None:
        args = _ns(
            recipe="memory-recent",
            base_url="http://127.0.0.1:8011",
            limit=3,
            filter_kind="event",
            include_quarantined=True,
            include_deleted=True,
            json=True,
        )
        res = mock.Mock(status=200, json={"results": [{"id": 11, "kind": "event", "summary": "S"}]})
        out = io.StringIO()
        with mock.patch("agent_memory_client.memory_recent", return_value=res) as recent_mock:
            with redirect_stdout(out):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 0)
        self.assertEqual(recent_mock.call_args.kwargs["limit"], 3)
        self.assertEqual(recent_mock.call_args.kwargs["kind"], "event")
        self.assertEqual(recent_mock.call_args.kwargs["include_quarantined"], True)
        self.assertEqual(recent_mock.call_args.kwargs["include_deleted"], True)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertEqual(rows[0]["record"]["id"], 11)

    def test_memory_retrieve_passes_filters_and_q_none(self) -> None:
        args = _ns(
            recipe="memory-retrieve",
            base_url="http://127.0.0.1:8011",
            q="",
            limit=7,
            filter_kind="fact",
            filter_module="modA",
            min_trust=0.6,
            max_age_sec=1234,
            json=True,
        )
        res = mock.Mock(status=200, json={"ok": True, "results": []})
        out = io.StringIO()
        with mock.patch("agent_memory_client.memory_retrieve", return_value=res) as retrieve_mock:
            with redirect_stdout(out):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 0)
        kwargs = retrieve_mock.call_args.kwargs
        self.assertIsNone(kwargs["q"])
        self.assertEqual(kwargs["module"], "modA")
        self.assertEqual(kwargs["min_trust"], 0.6)
        self.assertEqual(kwargs["max_age_sec"], 1234)

    def test_memory_feedback_success_non_json(self) -> None:
        args = _ns(
            recipe="memory-feedback",
            base_url="http://127.0.0.1:8011",
            id=9,
            rating=1,
            notes="ok",
            json=False,
        )
        out = io.StringIO()
        res = mock.Mock(status=200, json={"ok": True})
        with mock.patch("agent_memory_client.memory_feedback", return_value=res) as feedback_mock:
            with redirect_stdout(out):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 0)
        fb_args = feedback_mock.call_args.args
        self.assertEqual(int(fb_args[1]), 9)
        self.assertEqual(int(fb_args[2]), 1)
        self.assertIn("ok", out.getvalue())

    def test_gateway_json_loads_routes_and_passes_to_client(self) -> None:
        args = _ns(
            recipe="memory-search",
            base_url="http://127.0.0.1:8011",
            q="abc",
            gateway_json="routes.json",
            json=True,
        )
        res = mock.Mock(status=200, json={"results": []})
        out = io.StringIO()
        with (
            mock.patch("agent_memory_routes.load_gateway_routes", return_value={"memory": "http://127.0.0.1:8011"}) as routes_mock,
            mock.patch("agent_memory_client.memory_search", return_value=res) as search_mock,
            redirect_stdout(out),
        ):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 0)
        self.assertTrue(routes_mock.called)
        self.assertEqual(search_mock.call_args.kwargs["routes"], {"memory": "http://127.0.0.1:8011"})

    def test_task_add_invalid_prio_falls_back_to_p2(self) -> None:
        args = _ns(
            recipe="task-add",
            base_url="http://127.0.0.1:8011",
            title="demo",
            prio="unexpected",
            json=True,
        )
        fake = mock.Mock(status=200, json={"ok": True})
        with mock.patch("agent_memory_client.memory_write", return_value=fake) as write_mock:
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 0)
        tags = write_mock.call_args.kwargs["tags"]
        self.assertIn("prio:p2", tags)

    def test_task_close_requires_id(self) -> None:
        args = _ns(recipe="task-close", base_url="http://127.0.0.1:8011", id=None)
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("id required", err.getvalue())

    def test_tasks_pending_non_json_and_error_status(self) -> None:
        args = _ns(recipe="tasks-pending", base_url="http://127.0.0.1:8011", json=False, limit=1)
        tasks = mock.Mock(status=500, json={"results": [{"id": 1, "kind": "task", "summary": "A", "content": "Status: open"}]})
        events = mock.Mock(status=200, json={"results": []})
        out = io.StringIO()
        with mock.patch("agent_memory_client.memory_search", side_effect=[tasks, events]):
            with redirect_stdout(out):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 1)
        self.assertIn("A", out.getvalue())

    def test_mcp_python_not_found(self) -> None:
        args = _ns(recipe="mcp", cwd="C:/tmp")
        err = io.StringIO()
        with mock.patch("cli_cmd_localai._resolve_python_command", return_value=""):
            with redirect_stderr(err):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("python not found", err.getvalue())

    def test_assistant_returns_2_when_cwd_missing(self) -> None:
        args = _ns(recipe="reindex", cwd="X:/definitely_missing_dir")
        with (
            mock.patch("cli_cmd_localai._run_command") as run_mock,
            mock.patch("subprocess.Popen") as popen_mock,
        ):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertFalse(run_mock.called)
        self.assertFalse(popen_mock.called)

    def test_assistant_returns_2_when_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            args = _ns(recipe="smoke", cwd=td)
            with (
                mock.patch("cli_cmd_localai._run_command") as run_mock,
                mock.patch("subprocess.Popen") as popen_mock,
            ):
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertFalse(run_mock.called)
        self.assertFalse(popen_mock.called)

    def test_reindex_runs_command_when_target_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            (cwd / "reindex.ps1").write_text("", encoding="utf-8")
            args = _ns(recipe="reindex", cwd=str(cwd), daemon=False)
            with mock.patch("cli_cmd_localai._run_command", return_value=0) as run_mock:
                code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 0)
        self.assertTrue(run_mock.called)

    def test_smoke_daemon_tool_missing_returns_127(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            (cwd / "Smoke-Test.ps1").write_text("", encoding="utf-8")
            args = _ns(recipe="smoke", cwd=str(cwd), daemon=True)
            err = io.StringIO()
            with mock.patch("subprocess.Popen", side_effect=FileNotFoundError()):
                with redirect_stderr(err):
                    code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 127)
        self.assertIn("tool not found", err.getvalue())

    def test_unknown_recipe_returns_2(self) -> None:
        args = _ns(recipe="nope", cwd=".")
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_localai._cmd_localai_assistant(args)
        self.assertEqual(code, 2)
        self.assertIn("unknown recipe", err.getvalue())
