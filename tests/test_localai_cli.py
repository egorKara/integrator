import shutil
import io
import json
import unittest
from contextlib import contextmanager
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock

import agent_memory_client
from app import run


@contextmanager
def localai_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / ".tmp_localai_cli"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class LocalAiCliTests(unittest.TestCase):
    def test_localai_assistant_rag_daemon(self) -> None:
        with localai_case_dir() as root:
            target = root / "rag_server.py"
            target.write_text("", encoding="utf-8")
            with mock.patch("subprocess.Popen") as popen_mock:
                code = run(
                    [
                        "integrator",
                        "localai",
                        "assistant",
                        "rag",
                        "--cwd",
                        str(root),
                        "--daemon",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue(popen_mock.called)

    def test_localai_assistant_memory_write_requires_file(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = run(["integrator", "localai", "assistant", "memory-write"])
        self.assertEqual(code, 2)

    def test_localai_assistant_memory_write_calls_client(self) -> None:
        with localai_case_dir() as root:
            report = root / "report.md"
            report.write_text("hello", encoding="utf-8")
            with mock.patch("cli.memory_write_file") as write_mock:
                write_mock.return_value = [mock.Mock(status=200, json={"ok": True, "record": {"id": 1}})]
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = run(
                        [
                            "integrator",
                            "localai",
                            "assistant",
                            "memory-write",
                            "--base-url",
                            "http://127.0.0.1:8011",
                            "--content-file",
                            str(report),
                            "--summary",
                            "s",
                            "--json",
                        ]
                    )
            self.assertEqual(code, 0)
            self.assertTrue(write_mock.called)

    def test_localai_assistant_memory_write_does_not_leak_auth_token(self) -> None:
        with localai_case_dir() as root:
            report = root / "report.md"
            report.write_text("hello", encoding="utf-8")
            secret = "TOKEN_" + ("x" * 40)
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch("cli.memory_write_file") as write_mock:
                write_mock.return_value = [mock.Mock(status=200, json={"ok": True})]
                with redirect_stdout(out), redirect_stderr(err):
                    code = run(
                        [
                            "integrator",
                            "localai",
                            "assistant",
                            "memory-write",
                            "--base-url",
                            "http://127.0.0.1:8011",
                            "--content-file",
                            str(report),
                            "--auth-token",
                            secret,
                            "--json",
                        ]
                    )
            self.assertEqual(code, 0)
            self.assertNotIn(secret, out.getvalue())
            self.assertNotIn(secret, err.getvalue())

    def test_localai_assistant_memory_search_json_outputs_records(self) -> None:
        out = io.StringIO()
        res = agent_memory_client.HttpResult(
            status=200,
            body=b"{}",
            json={"ok": True, "results": [{"id": 1, "kind": "event", "summary": "s"}]},
        )
        with mock.patch("agent_memory_client.memory_search", return_value=res):
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "localai",
                        "assistant",
                        "memory-search",
                        "--base-url",
                        "http://127.0.0.1:8011",
                        "--q",
                        "x",
                        "--json",
                    ]
                )
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertEqual(rows[0]["record"]["id"], 1)

    def test_localai_assistant_memory_stats_json_outputs_wrapper(self) -> None:
        out = io.StringIO()
        res = agent_memory_client.HttpResult(status=200, body=b"{}", json={"ok": True, "stats": {"total": 1}})
        with mock.patch("agent_memory_client.memory_stats", return_value=res):
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "localai",
                        "assistant",
                        "memory-stats",
                        "--base-url",
                        "http://127.0.0.1:8011",
                        "--json",
                    ]
                )
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertEqual(rows[0]["status"], 200)
        self.assertTrue(rows[0]["json"]["ok"])

    def test_localai_assistant_tasks_pending_filters_closed(self) -> None:
        out = io.StringIO()

        def fake_search(
            base_url: str,
            q: str,
            *,
            limit: int = 10,
            kind: str | None = None,
            min_importance: float | None = None,
            include_quarantined: bool = False,
            include_deleted: bool = False,
            auth_token: str | None = None,
            routes: dict[str, str] | None = None,
        ) -> agent_memory_client.HttpResult:
            if q == "[TASK]":
                return agent_memory_client.HttpResult(
                    status=200,
                    body=b"{}",
                    json={
                        "ok": True,
                        "results": [{"id": 5, "kind": "task", "summary": "[TASK] t", "content": "Status: open"}],
                    },
                )
            return agent_memory_client.HttpResult(
                status=200,
                body=b"{}",
                json={
                    "ok": True,
                    "results": [{"id": 9, "kind": "event", "summary": "x", "content": "TaskId: 5\nStatus: done"}],
                },
            )

        with mock.patch("agent_memory_client.memory_search", side_effect=fake_search):
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "localai",
                        "assistant",
                        "tasks-pending",
                        "--base-url",
                        "http://127.0.0.1:8011",
                        "--json",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual([ln for ln in out.getvalue().splitlines() if ln.strip()], [])

    def test_localai_assistant_task_add_calls_memory_write(self) -> None:
        out = io.StringIO()
        with mock.patch(
            "agent_memory_client.memory_write",
            return_value=agent_memory_client.HttpResult(status=200, body=b"{}", json={"ok": True}),
        ) as write_mock:
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "localai",
                        "assistant",
                        "task-add",
                        "--base-url",
                        "http://127.0.0.1:8011",
                        "--title",
                        "t",
                        "--prio",
                        "p1",
                        "--owner",
                        "me",
                        "--next-step",
                        "do",
                        "--json",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertTrue(write_mock.called)
        args, kwargs = write_mock.call_args
        self.assertEqual(kwargs.get("kind"), "task")
        self.assertTrue(str(kwargs.get("summary") or "").startswith("[TASK] "))
        content = str(kwargs.get("content") or "")
        self.assertIn("Status: open", content)
        self.assertIn("Priority: p1", content)
        self.assertIn("Owner: me", content)
        self.assertIn("NextStep: do", content)

    def test_localai_assistant_task_close_calls_memory_write(self) -> None:
        out = io.StringIO()
        with mock.patch(
            "agent_memory_client.memory_write",
            return_value=agent_memory_client.HttpResult(status=200, body=b"{}", json={"ok": True}),
        ) as write_mock:
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "localai",
                        "assistant",
                        "task-close",
                        "--base-url",
                        "http://127.0.0.1:8011",
                        "--id",
                        "7",
                        "--notes",
                        "n",
                        "--json",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertTrue(write_mock.called)
        args, kwargs = write_mock.call_args
        self.assertEqual(kwargs.get("kind"), "event")
        self.assertEqual(str(kwargs.get("summary") or ""), "[TASK-CLOSE] 7")
        content = str(kwargs.get("content") or "")
        self.assertIn("TaskId: 7", content)
        self.assertIn("Status: done", content)
