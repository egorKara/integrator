import io
import json
import os
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from app import run


@contextmanager
def case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_case_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    prev = os.getcwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(prev)
        shutil.rmtree(root, ignore_errors=True)


class ZapovednikWorkflowTests(unittest.TestCase):
    def test_zapovednik_start_append_finalize_show(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "start", "--json"])
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            path = Path(str(row.get("path", "")))
            self.assertTrue(path.exists())

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        "hello?",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("hello?", path.read_text(encoding="utf-8"))

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "finalize", "--json"])
            self.assertEqual(code, 0)
            self.assertIn("Итоги и статистика", path.read_text(encoding="utf-8"))

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "show"])
            self.assertEqual(code, 0)
            self.assertIn("hello?", buf.getvalue())
