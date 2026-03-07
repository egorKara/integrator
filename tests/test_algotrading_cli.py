import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from app import run


class AlgoTradingCliTests(unittest.TestCase):
    def test_algotrading_doctor_detects_missing_pipeline_doc(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            vault = root / "vault"
            (assistant / "scripts").mkdir(parents=True)
            (assistant / "docs").mkdir(parents=True)
            (vault / "Specs").mkdir(parents=True)

            (assistant / "scripts" / "run_algo.py").write_text("print('ok')\n", encoding="utf-8")
            (assistant / "scripts" / "optimize_lessons.py").write_text("print('ok')\n", encoding="utf-8")
            (assistant / "scripts" / "media_db_migrate.py").write_text("print('ok')\n", encoding="utf-8")
            (assistant / "docs" / "API_Reference.md").write_text("# api\n", encoding="utf-8")
            (assistant / "docs" / "RAG_Service.md").write_text("# rag\n", encoding="utf-8")
            (vault / "Specs" / "SPEC-001-Pipeline.md").write_text("# spec\n", encoding="utf-8")
            (vault / "Specs" / "REQ-001-User-Feedback.md").write_text("# req\n", encoding="utf-8")
            (vault / "README.md").write_text("# readme\n", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "doctor",
                        "--assistant-root",
                        str(assistant),
                        "--vault-root",
                        str(vault),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue().strip().splitlines()[-1])
            self.assertTrue(payload["notes"]["pipeline_doc_missing"])

    def test_algotrading_sync_ssot_writes_doc(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            vault = root / "vault"
            (assistant / "docs").mkdir(parents=True)
            (vault / "Specs").mkdir(parents=True)

            (vault / "Specs" / "SPEC-001-Pipeline.md").write_text("# spec\n", encoding="utf-8")
            (vault / "Specs" / "REQ-001-User-Feedback.md").write_text("# req\n", encoding="utf-8")
            (vault / "README.md").write_text("# readme\n", encoding="utf-8")

            out = io.StringIO()
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "sync-ssot",
                        "--assistant-root",
                        str(assistant),
                        "--vault-root",
                        str(vault),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue().strip().splitlines()[-1])
            self.assertEqual(payload["status"], "written")
            self.assertTrue(Path(payload["path"]).exists())

            out2 = io.StringIO()
            with redirect_stdout(out2):
                code2 = run(
                    [
                        "integrator",
                        "algotrading",
                        "sync-ssot",
                        "--assistant-root",
                        str(assistant),
                        "--vault-root",
                        str(vault),
                        "--json",
                    ]
                )
            self.assertEqual(code2, 0)
            payload2 = json.loads(out2.getvalue().strip().splitlines()[-1])
            self.assertEqual(payload2["status"], "skipped_exists")

    def test_algotrading_config_init_fill_from_vault_sets_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vault = root / "vault"
            (vault / "Configs").mkdir(parents=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "config",
                        "init",
                        "--vault-root",
                        str(vault),
                        "--fill-from-vault",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue().strip().splitlines()[-1])
            cfg_path = Path(payload["path"])
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(cfg["out_dir"], str((vault / "processed").resolve()))
            self.assertEqual(cfg["env"]["ALGO_LESSONS_SOURCE"], cfg["out_dir"])

    def test_algotrading_run_auto_uses_default_config_by_vault_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            vault = root / "vault"
            (assistant / "scripts").mkdir(parents=True)
            (vault / "Configs").mkdir(parents=True)

            (assistant / "scripts" / "run_algo.py").write_text("print('run')\n", encoding="utf-8")

            cfg_path = vault / "Configs" / "algotrading.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "vault_root": str(vault),
                        "assistant_root": str(assistant),
                        "base_dir": "",
                        "out_dir": str((vault / "processed").resolve()),
                        "env": {"ALGO_METHOD_AUTO": "1"},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            out = io.StringIO()
            with redirect_stdout(out):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "run",
                        "--assistant-root",
                        str(assistant),
                        "--vault-root",
                        str(vault),
                        "--base",
                        str((root / "base").resolve()),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue().strip().splitlines()[-1])
            self.assertEqual(Path(payload["config_path"]).resolve(), cfg_path.resolve())

    def test_algotrading_run_env_precedence_cli_over_file_over_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            vault = root / "vault"
            (assistant / "scripts").mkdir(parents=True)
            (vault / "Configs").mkdir(parents=True)
            (vault / "processed").mkdir(parents=True)

            cfg_path = vault / "Configs" / "algotrading.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "vault_root": str(vault),
                        "assistant_root": str(assistant),
                        "base_dir": str((root / "base").resolve()),
                        "out_dir": str((vault / "processed").resolve()),
                        "env": {"ALGO_MODE": "cfg"},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            env_file = root / ".algo.env"
            env_file.write_text("ALGO_MODE=file\n", encoding="utf-8")

            captured_argv: list[str] = []
            captured_env: dict[str, str] = {}

            def _fake_run_python(python_cmd: str, cwd: Path, argv: list[str], *, extra_env: dict[str, str] | None):
                captured_argv[:] = list(argv)
                captured_env.clear()
                captured_env.update(dict(extra_env or {}))
                return 0, "ok", ""

            out = io.StringIO()
            with (
                mock.patch("cli_cmd_algotrading._resolve_python_command", return_value="python"),
                mock.patch("cli_cmd_algotrading._run_python", side_effect=_fake_run_python),
                redirect_stdout(out),
            ):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "run",
                        "--assistant-root",
                        str(assistant),
                        "--vault-root",
                        str(vault),
                        "--env-file",
                        str(env_file),
                        "--env",
                        "ALGO_MODE=cli",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(captured_env.get("ALGO_MODE"), "cli")

    def test_algotrading_optimize_lessons_uses_config_flags_and_cli_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            (assistant / "scripts").mkdir(parents=True)
            cfg_path = root / "algotrading.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "env": {"ALGO_MODE": "cfg"},
                        "optimize_lessons": {"source": "S", "write_versions": True, "no_index": True},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            captured_argv: list[str] = []
            captured_env: dict[str, str] = {}

            def _fake_run_python(python_cmd: str, cwd: Path, argv: list[str], *, extra_env: dict[str, str] | None):
                captured_argv[:] = list(argv)
                captured_env.clear()
                captured_env.update(dict(extra_env or {}))
                return 0, "", ""

            out = io.StringIO()
            with (
                mock.patch("cli_cmd_algotrading._resolve_python_command", return_value="python"),
                mock.patch("cli_cmd_algotrading._run_python", side_effect=_fake_run_python),
                redirect_stdout(out),
            ):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "optimize-lessons",
                        "--assistant-root",
                        str(assistant),
                        "--config",
                        str(cfg_path),
                        "--env",
                        "ALGO_MODE=cli",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("--source", captured_argv)
            self.assertIn("S", captured_argv)
            self.assertIn("--write-versions", captured_argv)
            self.assertIn("--no-index", captured_argv)
            self.assertEqual(captured_env.get("ALGO_MODE"), "cli")

    def test_algotrading_media_db_migrate_uses_config_flags_and_cli_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            (assistant / "scripts").mkdir(parents=True)
            cfg_path = root / "algotrading.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "env": {"ALGO_MODE": "cfg"},
                        "media_db_migrate": {"source": "SRC", "target": "DST", "dry_run": True, "move": True},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            captured_argv: list[str] = []
            captured_env: dict[str, str] = {}

            def _fake_run_python(python_cmd: str, cwd: Path, argv: list[str], *, extra_env: dict[str, str] | None):
                captured_argv[:] = list(argv)
                captured_env.clear()
                captured_env.update(dict(extra_env or {}))
                return 0, "", ""

            out = io.StringIO()
            with (
                mock.patch("cli_cmd_algotrading._resolve_python_command", return_value="python"),
                mock.patch("cli_cmd_algotrading._run_python", side_effect=_fake_run_python),
                redirect_stdout(out),
            ):
                code = run(
                    [
                        "integrator",
                        "algotrading",
                        "media-db-migrate",
                        "--assistant-root",
                        str(assistant),
                        "--config",
                        str(cfg_path),
                        "--env",
                        "ALGO_MODE=cli",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("--source", captured_argv)
            self.assertIn("SRC", captured_argv)
            self.assertIn("--target", captured_argv)
            self.assertIn("DST", captured_argv)
            self.assertIn("--dry-run", captured_argv)
            self.assertIn("--move", captured_argv)
            self.assertEqual(captured_env.get("ALGO_MODE"), "cli")

    def test_algotrading_run_returns_2_when_base_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            (assistant / "scripts").mkdir(parents=True)

            stderr = io.StringIO()
            with (
                mock.patch("cli_cmd_algotrading._resolve_python_command", return_value="python"),
                redirect_stdout(io.StringIO()),
                mock.patch("sys.stderr", stderr),
            ):
                code = run(["integrator", "algotrading", "run", "--assistant-root", str(assistant), "--json"])
            self.assertEqual(code, 2)
            self.assertIn("--base is required", stderr.getvalue())

    def test_algotrading_optimize_lessons_returns_2_when_python_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assistant = root / "assistant"
            (assistant / "scripts").mkdir(parents=True)

            stderr = io.StringIO()
            with (
                mock.patch("cli_cmd_algotrading._resolve_python_command", return_value=""),
                redirect_stdout(io.StringIO()),
                mock.patch("sys.stderr", stderr),
            ):
                code = run(
                    ["integrator", "algotrading", "optimize-lessons", "--assistant-root", str(assistant), "--json"]
                )
            self.assertEqual(code, 2)
            self.assertIn("python not found", stderr.getvalue())
