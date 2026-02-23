import io
import json
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from app import run


@contextmanager
def hygiene_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_hygiene_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class HygieneCliTests(unittest.TestCase):
    def test_hygiene_dry_run_does_not_delete(self) -> None:
        with hygiene_case_dir() as root:
            prj = root / "repo"
            prj.mkdir()
            (prj / "pyproject.toml").write_text("", encoding="utf-8")

            pyc = prj / "__pycache__"
            pyc.mkdir()
            (pyc / "x.pyc").write_text("x", encoding="utf-8")

            mypy = prj / ".mypy_cache"
            mypy.mkdir()

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "hygiene", "--roots", str(root), "--max-depth", "1", "--json"])
            self.assertEqual(code, 0)
            lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
            self.assertTrue(lines)
            payloads = [json.loads(ln) for ln in lines]
            rels = {p.get("rel", "") for p in payloads}
            self.assertIn("__pycache__", "\n".join(rels))
            self.assertIn(".mypy_cache", "\n".join(rels))
            self.assertTrue(pyc.exists())
            self.assertTrue(mypy.exists())

    def test_hygiene_apply_deletes_targets(self) -> None:
        with hygiene_case_dir() as root:
            prj = root / "repo"
            prj.mkdir()
            (prj / "pyproject.toml").write_text("", encoding="utf-8")

            pyc = prj / "__pycache__"
            pyc.mkdir()
            (pyc / "x.pyc").write_text("x", encoding="utf-8")

            tests_tmp = prj / "tests" / ".tmp_demo"
            tests_tmp.mkdir(parents=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "hygiene", "--roots", str(root), "--max-depth", "1", "--apply", "--json"])
            self.assertEqual(code, 0)
            self.assertFalse(pyc.exists())
            self.assertFalse(tests_tmp.exists())

