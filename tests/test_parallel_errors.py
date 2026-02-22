from __future__ import annotations

import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cli_parallel import WorkerError, _parallel_map
from scan import Project


class TestParallelMapErrors(unittest.TestCase):
    def test_parallel_map_returns_worker_error(self) -> None:
        def boom(x: int) -> int:
            raise RuntimeError(f"boom:{x}")

        items = [1, 2, 3]
        results = _parallel_map(items, boom, jobs=3)

        self.assertEqual({item for item, _ in results}, set(items))
        self.assertTrue(all(isinstance(value, WorkerError) for _, value in results))


class TestCliResilience(unittest.TestCase):
    def test_agents_status_json_does_not_crash_on_worker_error(self) -> None:
        import cli_cmd_agents as mod

        p = Project(name="p1", path=Path(r"C:\tmp\p1"))
        args = argparse.Namespace(
            roots=None,
            strict_roots=False,
            max_depth=4,
            jobs=4,
            project=None,
            limit=None,
            json=True,
            only_problems=False,
            fix_hints=False,
        )

        out = io.StringIO()
        with (
            patch.object(mod, "_projects_from_args", return_value=[p]),
            patch.object(mod, "_abort_if_roots_invalid", return_value=False),
            patch.object(mod, "_agent_projects", side_effect=lambda x: x),
            patch.object(mod, "_parallel_map", return_value=[(p, WorkerError("RuntimeError", "boom"))]),
            redirect_stdout(out),
        ):
            code = mod._cmd_agents_status(args)

        self.assertEqual(code, 0)
        line = out.getvalue().strip()
        payload = json.loads(line)
        self.assertEqual(payload["name"], "p1")
        self.assertIn("worker_error", payload.get("problems", []))

    def test_status_json_does_not_crash_on_worker_error(self) -> None:
        import cli_cmd_git as mod

        p = Project(name="p1", path=Path(r"C:\tmp\p1"))
        args = argparse.Namespace(
            roots=None,
            strict_roots=False,
            max_depth=3,
            jobs=4,
            project=None,
            limit=None,
            only_dirty=False,
            json=True,
        )

        out = io.StringIO()
        with (
            patch.object(mod, "_projects_from_args", return_value=[p]),
            patch.object(mod, "_abort_if_roots_invalid", return_value=False),
            patch.object(mod, "_map_git_projects", return_value=[(p, WorkerError("RuntimeError", "boom"))]),
            redirect_stdout(out),
        ):
            code = mod._cmd_status(args)

        self.assertEqual(code, 1)
        line = out.getvalue().strip()
        payload = json.loads(line)
        self.assertEqual(payload["name"], "p1")
        self.assertEqual(payload["state"], "error")
