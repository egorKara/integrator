import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from utils import (
    _apply_gitignore_lines,
    _coerce_int,
    _ensure_dir_exists,
    _ensure_file_exists,
    _load_global_gitignore,
    _path_exists_from_value,
    _read_gitignore_lines,
    _read_json_object,
    _run_capture,
    _run_command,
    _safe_file_count,
    _write_stream,
    _write_text_atomic,
)


class UtilsTests(unittest.TestCase):
    def test_load_global_gitignore_reads_lines(self) -> None:
        lines = _load_global_gitignore()
        self.assertIsInstance(lines, list)

    def test_read_gitignore_lines_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".gitignore"
            self.assertEqual(_read_gitignore_lines(p), [])

    def test_ensure_dir_exists_prints_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing"
            err = io.StringIO()
            with mock.patch("sys.stderr", err):
                ok = _ensure_dir_exists(missing, "root")
            self.assertFalse(ok)
            self.assertIn("root not found:", err.getvalue())

    def test_ensure_file_exists_prints_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.txt"
            err = io.StringIO()
            with mock.patch("sys.stderr", err):
                ok = _ensure_file_exists(missing, "file")
            self.assertFalse(ok)
            self.assertIn("file not found:", err.getvalue())

    def test_write_text_atomic_writes_and_backs_up(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.txt"
            target.write_text("old\n", encoding="utf-8")

            _write_text_atomic(target, "new\n", backup=True)

            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
            self.assertEqual((root / "a.txt.bak").read_text(encoding="utf-8"), "old\n")

    def test_write_text_atomic_backup_replace_error_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "a.txt"
            target.write_text("old\n", encoding="utf-8")

            orig_replace = Path.replace

            def replace(self: Path, dest: Path) -> Path:
                if str(dest).endswith(".bak"):
                    raise OSError("nope")
                return orig_replace(self, dest)

            with mock.patch.object(Path, "replace", new=replace):
                _write_text_atomic(target, "new\n", backup=True)

            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_apply_gitignore_lines_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".gitignore"
            p.write_text("a\n", encoding="utf-8")

            changed, missing, err = _apply_gitignore_lines(p, ["a", "b"], dry_run=True)

            self.assertTrue(changed)
            self.assertEqual(missing, ["b"])
            self.assertIsNone(err)
            self.assertEqual(p.read_text(encoding="utf-8"), "a\n")

    def test_apply_gitignore_lines_noop_when_no_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".gitignore"
            p.write_text("a\nb\n", encoding="utf-8")

            changed, missing, err = _apply_gitignore_lines(p, ["a", "b"], dry_run=False)

            self.assertFalse(changed)
            self.assertEqual(missing, [])
            self.assertIsNone(err)

    def test_apply_gitignore_lines_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".gitignore"
            p.write_text("a\n", encoding="utf-8")

            changed, missing, err = _apply_gitignore_lines(p, ["a", "b"], dry_run=False)

            self.assertTrue(changed)
            self.assertEqual(missing, ["b"])
            self.assertIsNone(err)
            self.assertEqual(p.read_text(encoding="utf-8"), "a\nb\n")

    def test_apply_gitignore_lines_writes_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".gitignore"

            changed, missing, err = _apply_gitignore_lines(p, ["a"], dry_run=False)

            self.assertTrue(changed)
            self.assertEqual(missing, ["a"])
            self.assertIsNone(err)
            self.assertEqual(p.read_text(encoding="utf-8"), "a\n")

    def test_apply_gitignore_lines_write_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".gitignore"
            p.write_text("a\n", encoding="utf-8")

            with mock.patch("utils._write_text_atomic", side_effect=OSError("disk")):
                changed, missing, err = _apply_gitignore_lines(p, ["a", "b"], dry_run=False)

            self.assertFalse(changed)
            self.assertEqual(missing, ["b"])
            self.assertEqual(err, "disk")

    def test_read_json_object_parses_dict_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            good = root / "good.json"
            good.write_text('{"a": 1}', encoding="utf-8")
            self.assertEqual(_read_json_object(good), {"a": 1})

            bad = root / "bad.json"
            bad.write_text("{", encoding="utf-8")
            self.assertIsNone(_read_json_object(bad))

            arr = root / "arr.json"
            arr.write_text("[1,2]", encoding="utf-8")
            self.assertIsNone(_read_json_object(arr))

    def test_safe_file_count_handles_permission_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(Path, "glob", side_effect=PermissionError()):
                self.assertEqual(_safe_file_count(root, "*.txt"), 0)

    def test_safe_file_count_returns_zero_for_non_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "x.txt"
            f.write_text("x", encoding="utf-8")
            self.assertEqual(_safe_file_count(f, "*.txt"), 0)

    def test_coerce_int(self) -> None:
        self.assertEqual(_coerce_int(True), 1)
        self.assertEqual(_coerce_int(False), 0)
        self.assertEqual(_coerce_int(5), 5)
        self.assertEqual(_coerce_int(" 7 "), 7)
        self.assertEqual(_coerce_int("x", default=9), 9)
        self.assertEqual(_coerce_int(object(), default=8), 8)

    def test_path_exists_from_value_rejects_invalid(self) -> None:
        self.assertFalse(_path_exists_from_value(None))
        self.assertFalse(_path_exists_from_value(""))
        self.assertFalse(_path_exists_from_value("   "))
        with mock.patch("pathlib.Path.exists", side_effect=OSError("boom")):
            self.assertFalse(_path_exists_from_value(r"C:\x"))

    def test_run_command_and_capture_error_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)

            self.assertEqual(_run_command([], cwd), 0)
            self.assertEqual(_run_capture([], cwd), (0, "", ""))

            with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
                err = io.StringIO()
                with mock.patch("sys.stderr", err):
                    self.assertEqual(_run_command(["missing_tool"], cwd), 127)
                self.assertIn("tool not found: missing_tool", err.getvalue())
                self.assertEqual(_run_capture(["missing_tool"], cwd), (127, "", "tool not found: missing_tool"))

            with mock.patch("subprocess.run", side_effect=OSError("x")):
                self.assertEqual(_run_capture(["tool"], cwd), (1, "", "x"))

    def test_write_stream_adds_newline(self) -> None:
        buf = io.StringIO()
        _write_stream(buf, "x")
        self.assertEqual(buf.getvalue(), "x\n")
        _write_stream(buf, "")
        self.assertEqual(buf.getvalue(), "x\n")
