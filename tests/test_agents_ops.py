import json
import shutil
import unittest
from pathlib import Path
from unittest import mock

from agents_ops import _agent_project_type, _agent_fix_hints, _agent_row_problems, _build_agent_row, _is_endpoint_up, _problem_tags
from git_ops import GitStatus
from scan import Project


class AgentsOpsTest(unittest.TestCase):
    def tearDown(self) -> None:
        parent = Path(__file__).resolve().parent
        for path in parent.glob(".tmp_agents_ops_*"):
            shutil.rmtree(path, ignore_errors=True)

    def test_is_endpoint_up_rejects_empty_and_invalid(self) -> None:
        self.assertFalse(_is_endpoint_up(""))
        self.assertFalse(_is_endpoint_up("not-a-url"))
        self.assertFalse(_is_endpoint_up("http:///missing-host"))

    def test_is_endpoint_up_true_when_socket_connects(self) -> None:
        class _Conn:
            def __enter__(self) -> object:
                return object()

            def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
                return None

        with mock.patch("agents_ops.socket.create_connection", return_value=_Conn()):
            self.assertTrue(_is_endpoint_up("http://127.0.0.1:8011"))

    def test_gateway_problems_and_fix_hints_deduplicate(self) -> None:
        path = Path("C:/demo/agent_gateway")
        row = {
            "path": str(path),
            "agent_type": "gateway",
            "state": "ok",
            "gateway_base": "",
            "gateway_routes": 0,
            "gateway_up": False,
        }
        problems = _agent_row_problems(row)
        self.assertIn("gateway_base_missing", problems)

        hints = _agent_fix_hints(row)
        expected = f"Get-Content {Path(str(path)).resolve() / 'config' / 'gateway.json'}"
        self.assertEqual(hints, [expected])

    def test_media_storage_problems_and_fix_hints(self) -> None:
        path = Path("C:/demo/media_storage")
        row = {
            "path": str(path),
            "agent_type": "media-storage",
            "state": "ok",
            "media_root": "C:/data/media",
            "media_root_exists": False,
            "work_root": "C:/data/work",
            "work_root_exists": False,
            "publish_root": "",
            "publish_root_exists": False,
        }
        problems = _agent_row_problems(row)
        self.assertIn("media_root_missing", problems)
        self.assertIn("work_root_missing", problems)
        self.assertIn("publish_root_empty", problems)

        hints = _agent_fix_hints(row)
        self.assertIn("Test-Path C:/data/media", hints)
        self.assertIn("New-Item -ItemType Directory -Force -Path C:/data/work", hints)

    def test_agent_project_type_detects_types(self) -> None:
        root = Path(__file__).resolve().parent / ".tmp_agents_ops_types"
        root.mkdir(parents=True, exist_ok=True)

        gateway = root / "gateway"
        (gateway / "config").mkdir(parents=True, exist_ok=True)
        (gateway / "config" / "gateway.json").write_text("{}", encoding="utf-8")
        self.assertEqual(_agent_project_type(gateway), "gateway")

        media = root / "media"
        (media / "config").mkdir(parents=True, exist_ok=True)
        (media / "config" / "media_paths.json").write_text("{}", encoding="utf-8")
        self.assertEqual(_agent_project_type(media), "media-storage")

        trae = root / "trae"
        (trae / ".trae" / "rules").mkdir(parents=True, exist_ok=True)
        (trae / ".trae" / "rules" / "project_rules.md").write_text("# rules\n", encoding="utf-8")
        self.assertEqual(_agent_project_type(trae), "trae-project")

        wf = root / "wf"
        wf.mkdir(parents=True, exist_ok=True)
        with mock.patch("scan._is_agent_project_dir", return_value=True):
            self.assertEqual(_agent_project_type(wf), "agent-workflow")

    def test_problem_tags_returns_empty_for_non_list(self) -> None:
        self.assertEqual(_problem_tags({"problems": "x"}), [])
        self.assertEqual(_problem_tags({"problems": [1, "a"]}), ["1", "a"])

    def test_build_agent_row_collects_fields_and_problems(self) -> None:
        root = Path(__file__).resolve().parent / ".tmp_agents_ops_row"
        (root / ".git").mkdir(parents=True, exist_ok=True)
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "scripts" / "a.ps1").write_text("x", encoding="utf-8")
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "config" / "gateway.json").write_text(
            json.dumps({"base_url": "http://127.0.0.1:8011", "routes": {}}),
            encoding="utf-8",
        )
        (root / "config" / "media_paths.json").write_text(
            json.dumps({"media_root": "", "work_root": "", "publish_root": ""}),
            encoding="utf-8",
        )

        prj = Project(name="p", path=root)
        gs = GitStatus(
            branch="main",
            upstream="",
            ahead=0,
            behind=0,
            clean=True,
            changed=0,
            untracked=0,
            raw="## main",
        )

        with (
            mock.patch("agents_ops._git_status", return_value=gs),
            mock.patch("agents_ops._is_endpoint_up", return_value=False),
        ):
            row = _build_agent_row(prj)

        self.assertEqual(row["name"], "p")
        self.assertEqual(row["state"], "clean")
        self.assertEqual(row["scripts"], 1)
        problems = row.get("problems", [])
        assert isinstance(problems, list)
        self.assertIn("gateway_routes_missing", problems)
        self.assertIn("gateway_unreachable", problems)
