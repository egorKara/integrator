import argparse
import tempfile
import unittest
from pathlib import Path

from tools.telegram_github_worker import _build_config, _load_state, _save_state


class TelegramGithubWorkerTests(unittest.TestCase):
    def test_build_config_from_args(self) -> None:
        args = argparse.Namespace(
            repo="egorKara/integrator",
            labels="remote, telegram",
            state_file="reports/state.json",
            queue_file="reports/queue.jsonl",
            dry_run=True,
            max_state_items=5000,
        )
        config = _build_config(args)
        self.assertEqual(config.repo_owner, "egorKara")
        self.assertEqual(config.repo_name, "integrator")
        self.assertEqual(config.labels, ["remote", "telegram"])
        self.assertTrue(config.dry_run)

    def test_build_config_invalid_repo(self) -> None:
        args = argparse.Namespace(
            repo="bad-repo",
            labels="remote,telegram",
            state_file="reports/state.json",
            queue_file="reports/queue.jsonl",
            dry_run=False,
            max_state_items=5000,
        )
        with self.assertRaises(RuntimeError):
            _build_config(args)

    def test_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            _save_state(path, processed={3, 1, 2}, max_items=5000)
            loaded = _load_state(path)
            self.assertEqual(loaded, {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
