import shutil
import unittest
from contextlib import contextmanager
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
