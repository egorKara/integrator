import io
import json
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from unittest import mock

from app import run
from cli import default_roots


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

    def test_default_roots_uses_env_roots_and_splits_semicolon(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "INTEGRATOR_ROOTS": " C:\\A ; ; C:\\B; ",
                "TAST_ROOTS": "",
                "INTEGRATOR_REGISTRY": "",
            },
            clear=False,
        ):
            roots = default_roots()
        self.assertEqual([str(path) for path in roots], ["C:\\A", "C:\\B"])

    def test_default_roots_env_overrides_registry(self) -> None:
        with registry_case_dir() as root:
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps([{"name": "x", "root": "C:\\vault\\Projects\\LocalAI", "status": "active"}], ensure_ascii=False),
                encoding="utf-8",
            )
            with mock.patch.dict(
                "os.environ",
                {
                    "INTEGRATOR_REGISTRY": str(registry_path),
                    "INTEGRATOR_ROOTS": "C:\\EnvRoot",
                    "TAST_ROOTS": "C:\\Ignored",
                },
                clear=False,
            ):
                roots = default_roots()
        self.assertEqual([str(path) for path in roots], ["C:\\EnvRoot"])

    def test_default_roots_uses_tast_roots_when_integrator_roots_empty(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "INTEGRATOR_ROOTS": "",
                "TAST_ROOTS": "C:\\T1;C:\\T2",
                "INTEGRATOR_REGISTRY": "",
            },
            clear=False,
        ):
            roots = default_roots()
        self.assertEqual([str(path) for path in roots], ["C:\\T1", "C:\\T2"])

    def test_registry_list_falls_back_to_embedded_defaults(self) -> None:
        buf = io.StringIO()
        with mock.patch("registry._default_registry_path", return_value=None):
            with redirect_stdout(buf):
                code = run(["integrator", "registry", "list", "--json"])
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
        self.assertTrue(any(row.get("name") == "integrator" for row in rows))
