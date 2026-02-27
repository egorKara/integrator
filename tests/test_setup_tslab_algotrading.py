import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar


def _load_setup_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "setup_tslab_algotrading.py"
    spec = importlib.util.spec_from_file_location("setup_tslab_algotrading", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupTslabAlgoTradingTests(unittest.TestCase):
    mod: ClassVar[Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_setup_module()

    def test_parser_defaults_follow_video_canon(self) -> None:
        parser = self.mod._build_parser()
        args = parser.parse_args(["moex"])

        self.assertEqual(args.provider_name, self.mod.VIDEO_CANON_PROVIDER_NAME)
        self.assertEqual(args.provider_type_label, self.mod.VIDEO_CANON_PROVIDER_TYPE_LABEL)
        self.assertEqual(args.video_lesson_id, self.mod.VIDEO_CANON_LESSON_ID)
        self.assertEqual(args.digits, 4)
        self.assertEqual(args.money_digits, 2)
        self.assertEqual(args.price_step, 0.0)
        self.assertEqual(args.lot_size, 1.0)
        self.assertEqual(args.lot_step, 1.0)
        self.assertEqual(args.currency, "Pt")

    def test_cmd_moex_writes_video_canon_artifacts(self) -> None:
        mod = self.mod
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            algo_root = temp_root / "AlgoTrading"
            (algo_root / "Configs").mkdir(parents=True, exist_ok=True)
            (algo_root / "Configs" / "algotrading.json").write_text("{}\n", encoding="utf-8")

            fake_exe = temp_root / "TSLab.exe"
            fake_exe.write_text("", encoding="utf-8")

            parser = mod._build_parser()
            args = parser.parse_args(
                [
                    "moex",
                    "--algo-root",
                    str(algo_root),
                    "--secid",
                    "SBRF",
                    "--from",
                    "2024-01-01",
                    "--till",
                    "2024-01-10",
                    "--interval",
                    "24",
                    "--tslab-exe",
                    str(fake_exe),
                    "--json",
                ]
            )
            args.secids = ["SBRF"]

            def fake_download_moex_bundle(**kwargs):
                offline_root = kwargs["offline_root"]
                offline_root.mkdir(parents=True, exist_ok=True)
                (offline_root / "SBRF_D1.csv").write_text(
                    "2024-01-01;00:00:00;1;2;0.5;1.5;10\n",
                    encoding="utf-8",
                )
                return (
                    [
                        {
                            "secid": "SBRF",
                            "path": str(offline_root / "SBRF_D1.csv"),
                            "status": "written",
                            "bars": 1,
                        }
                    ],
                    [],
                )

            original_download = mod._download_moex_bundle
            mod._download_moex_bundle = fake_download_moex_bundle
            try:
                rc = mod._cmd_moex(args)
            finally:
                mod._download_moex_bundle = original_download

            self.assertEqual(rc, 0)

            manifest_path = algo_root / "TSLab" / "Manifests" / "offline_provider_moex.json"
            runbook_path = algo_root / "TSLab" / "Runbooks" / "TSLab_Offline_Provider_Quickstart.md"
            config_path = algo_root / "Configs" / "algotrading.json"

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            runbook = runbook_path.read_text(encoding="utf-8")

            self.assertEqual(manifest["provider"]["name"], "Finam_txt")
            self.assertEqual(manifest["provider"]["ui_type_label"], "Текстовые файлы")
            self.assertEqual(manifest["provider"]["ui_settings"]["digits"], 4)
            self.assertEqual(manifest["provider"]["ui_settings"]["money_digits"], 2)
            self.assertEqual(manifest["provider"]["ui_settings"]["price_step"], 0.0)
            self.assertEqual(manifest["provider"]["ui_settings"]["lot_size"], 1.0)
            self.assertEqual(manifest["provider"]["ui_settings"]["lot_step"], 1.0)
            self.assertEqual(manifest["provider"]["ui_settings"]["currency"], "Pt")
            self.assertEqual(manifest["canon"]["lesson_id"], mod.VIDEO_CANON_LESSON_ID)

            self.assertEqual(cfg["tslab"]["provider"]["name"], "Finam_txt")
            self.assertEqual(cfg["tslab"]["provider"]["ui_type_label"], "Текстовые файлы")
            self.assertEqual(cfg["tslab"]["provider"]["ui_settings"]["digits"], 4)
            self.assertEqual(cfg["tslab"]["video_canon"]["lesson_id"], mod.VIDEO_CANON_LESSON_ID)

            self.assertIn("Имя поставщика: `Finam_txt`.", runbook)
            self.assertIn("Количество знаков: `4`.", runbook)
            self.assertIn("Количество денежных знаков: `2`.", runbook)
            self.assertIn("Шаг цены: `0`.", runbook)
            self.assertIn("Размер лота: `1`.", runbook)
            self.assertIn("Шаг лота: `1`.", runbook)
            self.assertIn("Валюта: `Pt`.", runbook)


if __name__ == "__main__":
    unittest.main()
