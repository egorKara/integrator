import io
import json
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock

from integrator.app import run
from integrator.cli import default_roots


@contextmanager
def registry_case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / ".tmp_registry"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class RegistryTests(unittest.TestCase):
    def test_registry_list_json(self) -> None:
        with registry_case_dir() as root:
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    [
                        {
                            "name": "localai",
                            "root": "C:\\vault\\Projects\\LocalAI",
                            "status": "active",
                            "priority": "p0",
                            "entrypoint": "C:\\LocalAI\\assistant",
                            "tags": ["rag", "kb"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "registry",
                        "list",
                        "--registry",
                        str(registry_path),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "localai")

    def test_default_roots_uses_registry(self) -> None:
        with registry_case_dir() as root:
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    [
                        {
                            "name": "localai",
                            "root": "C:\\vault\\Projects\\LocalAI",
                            "status": "active",
                            "priority": "p0",
                            "entrypoint": "C:\\LocalAI\\assistant",
                            "tags": ["rag", "kb"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                "os.environ",
                {
                    "INTEGRATOR_REGISTRY": str(registry_path),
                    "INTEGRATOR_ROOTS": "",
                    "TAST_ROOTS": "",
                },
                clear=False,
            ):
                roots = default_roots()
            self.assertEqual([str(path) for path in roots], ["C:\\vault\\Projects\\LocalAI"])
