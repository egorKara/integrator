import tempfile
import unittest
from pathlib import Path
from unittest import mock

from git_ops import _git_origin_url, _git_status, _git_status_fields, _normalize_github, _parse_git_branch_line, _resolve_git_dir


class GitOpsTests(unittest.TestCase):
    def test_parse_git_branch_line_variants(self) -> None:
        self.assertEqual(_parse_git_branch_line("## main"), ("main", "", 0, 0))
        self.assertEqual(_parse_git_branch_line("## main...origin/main"), ("main", "origin/main", 0, 0))
        self.assertEqual(
            _parse_git_branch_line("## main...origin/main [ahead 2, behind 1]"),
            ("main", "origin/main", 2, 1),
        )

    def test_resolve_git_dir_dir_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gitdir = root / ".git"
            gitdir.mkdir()
            self.assertEqual(_resolve_git_dir(root), gitdir)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / ".real_git"
            real.mkdir()
            gitfile = root / ".git"
            gitfile.write_text("gitdir: .real_git\n", encoding="utf-8")
            resolved = _resolve_git_dir(root)
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertTrue(resolved.samefile(real))

    def test_git_status_none_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(_git_status(Path(td)))

    def test_git_status_error_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()

            with mock.patch("git_ops._resolve_git_dir", return_value=None):
                gs = _git_status(root)
            self.assertIsNotNone(gs)
            assert gs is not None
            self.assertEqual(gs.raw, "invalid .git")
            self.assertEqual(_git_status_fields(gs)["state"], "error")

            with mock.patch("utils._run_capture", return_value=(127, "", "tool not found: git")):
                gs2 = _git_status(root)
            assert gs2 is not None
            self.assertEqual(_git_status_fields(gs2)["state"], "tool-missing")

    def test_git_status_parses_changed_and_untracked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            out = "## main...origin/main [ahead 1, behind 2]\n M a.txt\n?? b.txt\n"
            with mock.patch("utils._run_capture", return_value=(0, out, "")):
                gs = _git_status(root)
            assert gs is not None
            self.assertFalse(gs.clean)
            self.assertEqual(gs.changed, 1)
            self.assertEqual(gs.untracked, 1)
            fields = _git_status_fields(gs)
            self.assertEqual(fields["branch"], "main")
            self.assertEqual(fields["upstream"], "origin/main")
            self.assertEqual(fields["ahead"], 1)
            self.assertEqual(fields["behind"], 2)

    def test_git_origin_url_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            with mock.patch("utils._run_capture", return_value=(0, "git@github.com:a/b.git\n", "")):
                url = _git_origin_url(root)
            self.assertEqual(url, "git@github.com:a/b.git")
            self.assertEqual(_normalize_github(url), "https://github.com/a/b")
