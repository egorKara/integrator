import io
import json
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock

from integrator.app import run


@contextmanager
def chains_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / ".tmp_chains"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class ChainsTests(unittest.TestCase):
    def test_chains_list_json(self) -> None:
        with chains_case_dir() as root:
            chains_path = root / "chains.json"
            chains_path.write_text(
                json.dumps(
                    [
                        {
                            "name": "health",
                            "description": "Health check",
                            "steps": [["python", "-m", "integrator", "doctor"]],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with mock.patch.dict("os.environ", {"INTEGRATOR_CHAINS": str(chains_path)}, clear=False):
                with redirect_stdout(buf):
                    code = run(["integrator", "chains", "list", "--json"])
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "health")

    def test_chains_plan_json(self) -> None:
        with chains_case_dir() as root:
            chains_path = root / "chains.json"
            chains_path.write_text(
                json.dumps(
                    [
                        {
                            "name": "health",
                            "description": "Health check",
                            "steps": [["python", "-m", "integrator", "doctor"]],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with mock.patch.dict("os.environ", {"INTEGRATOR_CHAINS": str(chains_path)}, clear=False):
                with redirect_stdout(buf):
                    code = run(["integrator", "chains", "plan", "health", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue().strip())
            self.assertEqual(payload["name"], "health")
            self.assertEqual(payload["steps"], [["python", "-m", "integrator", "doctor"]])
