import shutil
import io
import unittest
from contextlib import contextmanager
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock

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
