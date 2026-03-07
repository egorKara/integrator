import argparse
import tempfile
import unittest
from pathlib import Path

from tools.telegram_github_executor import _build_config, _extract_request_text, _load_started, _save_started


class TelegramGithubExecutorTests(unittest.TestCase):
    def test_extract_request_text(self) -> None:
        body = "Источник\nЗапрос:\nсделай проверку статуса задач"
        self.assertEqual(_extract_request_text(body), "сделай проверку статуса задач")

    def test_build_config(self) -> None:
        args = argparse.Namespace(
            repo="egorKara/integrator",
            state_file="reports/executor_state.json",
            plans_dir="reports/plans",
            max_start_per_cycle=2,
            dry_run=True,
        )
        config = _build_config(args)
        self.assertEqual(config.repo_owner, "egorKara")
        self.assertEqual(config.repo_name, "integrator")
        self.assertEqual(config.max_start_per_cycle, 2)
        self.assertTrue(config.dry_run)

    def test_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            _save_started(path, {10, 11})
            loaded = _load_started(path)
            self.assertEqual(loaded, {10, 11})


if __name__ == "__main__":
    unittest.main()
