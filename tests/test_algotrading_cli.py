import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

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
            self.assertEqual(cfg["out_dir"], str((vault / "data" / "processed").resolve()))
            self.assertEqual(cfg["env"]["ALGO_LESSONS_SOURCE"], cfg["out_dir"])
