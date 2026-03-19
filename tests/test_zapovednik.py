import io
import json
import os
import shutil
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from app import run
from zapovednik import session_health
from zapovednik_policy import get_policy


@contextmanager
def case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_case_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    prev = os.getcwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(prev)
        shutil.rmtree(root, ignore_errors=True)


class ZapovednikWorkflowTests(unittest.TestCase):
    def _assert_zapovednik_start_json_contract(self, payload: dict[str, object]) -> None:
        self.assertEqual(set(payload.keys()), {"kind", "path", "path_masked", "success"})
        self.assertEqual(payload.get("kind"), "zapovednik_start")
        self.assertIsInstance(payload.get("path"), str)
        self.assertIsInstance(payload.get("path_masked"), bool)
        self.assertIsInstance(payload.get("success"), bool)

    def test_session_open_alias_returns_success_and_absolute_path(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "session", "open", "--json"])
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            self._assert_zapovednik_start_json_contract(row)
            path = Path(str(row.get("path", "")))
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.exists())
            self.assertFalse(bool(row.get("path_masked")))
            self.assertTrue(bool(row.get("success")))

    def test_session_open_redacts_sensitive_path_segments(self) -> None:
        secret_segment = f"token_sk_live_{uuid4().hex}{uuid4().hex}"
        root = Path(__file__).resolve().parent / f".tmp_case_{secret_segment}"
        root.mkdir(parents=True, exist_ok=True)
        prev = os.getcwd()
        os.chdir(root)
        try:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "session", "open", "--json"])
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            self._assert_zapovednik_start_json_contract(row)
            self.assertTrue(bool(row.get("path_masked")))
            path_out = str(row.get("path", ""))
            self.assertIn("[REDACTED]", path_out)
            self.assertNotIn(secret_segment, path_out)
        finally:
            os.chdir(prev)
            shutil.rmtree(root, ignore_errors=True)

    def test_zapovednik_start_append_finalize_show(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "start", "--json"])
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            self._assert_zapovednik_start_json_contract(row)
            path = Path(str(row.get("path", "")))
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.exists())
            self.assertFalse(bool(row.get("path_masked")))
            self.assertTrue(bool(row.get("success")))

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        "hello?",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("hello?", path.read_text(encoding="utf-8"))

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "finalize", "--json"])
            self.assertEqual(code, 0)
            self.assertIn("Итоги и статистика", path.read_text(encoding="utf-8"))

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "show", "--path", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("hello?", buf.getvalue())

    def test_finalize_then_append_starts_new_session(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "start", "--json"])
            self.assertEqual(code, 0)
            start_row = json.loads(buf.getvalue().strip())
            first_path = Path(str(start_row.get("path", "")))
            self.assertTrue(first_path.exists())

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        "first session message",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "finalize", "--json"])
            self.assertEqual(code, 0)
            first_text = first_path.read_text(encoding="utf-8")
            self.assertIn("- session_closed: true", first_text)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        "second session message",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            append_row = json.loads(buf.getvalue().strip())
            second_path = Path(str(append_row.get("path", "")))
            self.assertNotEqual(first_path, second_path)
            self.assertIn("second session message", second_path.read_text(encoding="utf-8"))
            self.assertNotIn("second session message", first_path.read_text(encoding="utf-8"))

    def test_zapovednik_health_json_recommend_close_machine_checkable(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "start", "--json"])
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            path = Path(str(row.get("path", "")))
            self.assertTrue(path.exists())

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        ("x " * 3000).strip(),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "health",
                        "--json",
                        "--path",
                        str(path),
                        "--context-window-tokens",
                        "100",
                        "--score-threshold",
                        "0.1",
                    ]
                )
            self.assertEqual(code, 0)
            health = json.loads(buf.getvalue().strip())
            self.assertEqual(health.get("kind"), "zapovednik_health")
            self.assertTrue(bool(health.get("recommend_close")))
            self.assertIsInstance(health.get("recommend_close_reasons"), list)
            self.assertIsInstance(health.get("close_score"), float)
            self.assertIsInstance(health.get("signals"), dict)
            self.assertIsInstance(health.get("thresholds"), dict)
            self.assertGreaterEqual(int(health.get("approx_tokens", 0)), 100)

    def test_append_auto_finalize_on_threshold_rotates_session(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "start", "--json"])
            self.assertEqual(code, 0)
            start_row = json.loads(buf.getvalue().strip())
            first_path = Path(str(start_row.get("path", "")))
            self.assertTrue(first_path.exists())

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        ("x " * 3000).strip(),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "append",
                        "--role",
                        "user",
                        "--text",
                        "after auto finalize",
                        "--auto-finalize-on-threshold",
                        "--context-window-tokens",
                        "100",
                        "--score-threshold",
                        "0.1",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            self.assertTrue(bool(row.get("recommend_close_before_append")))
            self.assertTrue(bool(row.get("auto_finalize_triggered")))
            self.assertIsInstance(row.get("auto_finalize_reasons"), list)
            second_path = Path(str(row.get("path", "")))
            self.assertNotEqual(first_path, second_path)
            first_text = first_path.read_text(encoding="utf-8")
            self.assertIn("- session_closed: true", first_text)
            self.assertIn("after auto finalize", second_path.read_text(encoding="utf-8"))

    def test_zapovednik_health_uses_profile_and_cli_overrides(self) -> None:
        with case_dir() as root:
            mem = root / ".trae" / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(["integrator", "workflow", "zapovednik", "start", "--json"])
            self.assertEqual(code, 0)
            row = json.loads(buf.getvalue().strip())
            path = Path(str(row.get("path", "")))
            self.assertTrue(path.exists())

            expected = get_policy("ops")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "health",
                        "--json",
                        "--path",
                        str(path),
                        "--profile",
                        "ops",
                    ]
                )
            self.assertEqual(code, 0)
            health = json.loads(buf.getvalue().strip())
            self.assertEqual(health.get("profile"), "ops")
            thresholds = health.get("thresholds", {})
            self.assertIsInstance(thresholds, dict)
            if isinstance(thresholds, dict):
                self.assertEqual(int(thresholds.get("message_soft_limit", -1)), int(expected["message_soft_limit"]))
                self.assertAlmostEqual(float(thresholds.get("token_hard_ratio", -1.0)), float(expected["token_hard_ratio"]))

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run(
                    [
                        "integrator",
                        "workflow",
                        "zapovednik",
                        "health",
                        "--json",
                        "--path",
                        str(path),
                        "--profile",
                        "ops",
                        "--message-soft-limit",
                        "99",
                    ]
                )
            self.assertEqual(code, 0)
            override_health = json.loads(buf.getvalue().strip())
            override_thresholds = override_health.get("thresholds", {})
            self.assertIsInstance(override_thresholds, dict)
            if isinstance(override_thresholds, dict):
                self.assertEqual(int(override_thresholds.get("message_soft_limit", -1)), 99)
                self.assertAlmostEqual(
                    float(override_thresholds.get("token_hard_ratio", -1.0)),
                    float(expected["token_hard_ratio"]),
                )

    def _write_synthetic_session(self, path: Path, messages: int, chars_per_message: int) -> None:
        chunks = ["## Сессия: synthetic\n\n"]
        payload = ("alpha beta gamma delta " * ((chars_per_message // 24) + 2))[:chars_per_message]
        for _ in range(messages):
            chunks.append("### msg\n- meta: {\"role\":\"user\"}\n- text:\n\n")
            chunks.append(payload)
            chunks.append("\n\n")
        path.write_text("".join(chunks), encoding="utf-8")

    def test_profile_thresholds_are_ordered_by_sensitivity(self) -> None:
        research = get_policy("research")
        coding = get_policy("coding")
        ops = get_policy("ops")
        self.assertGreater(int(research["message_soft_limit"]), int(coding["message_soft_limit"]))
        self.assertGreater(int(coding["message_soft_limit"]), int(ops["message_soft_limit"]))
        self.assertGreater(int(research["size_soft_limit_kb"]), int(coding["size_soft_limit_kb"]))
        self.assertGreater(int(coding["size_soft_limit_kb"]), int(ops["size_soft_limit_kb"]))
        self.assertGreater(float(research["score_threshold"]), float(coding["score_threshold"]))
        self.assertGreater(float(coding["score_threshold"]), float(ops["score_threshold"]))

    def test_profile_calibration_ops_closes_earlier_than_coding(self) -> None:
        with case_dir() as root:
            sample = root / "ops_case.md"
            self._write_synthetic_session(sample, messages=30, chars_per_message=3500)
            ops = session_health(path=sample, **get_policy("ops"))
            coding = session_health(path=sample, **get_policy("coding"))
            research = session_health(path=sample, **get_policy("research"))
            self.assertTrue(bool(ops["recommend_close"]))
            self.assertFalse(bool(coding["recommend_close"]))
            self.assertFalse(bool(research["recommend_close"]))

    def test_profile_calibration_coding_closes_earlier_than_research(self) -> None:
        with case_dir() as root:
            sample = root / "coding_case.md"
            self._write_synthetic_session(sample, messages=50, chars_per_message=4500)
            ops = session_health(path=sample, **get_policy("ops"))
            coding = session_health(path=sample, **get_policy("coding"))
            research = session_health(path=sample, **get_policy("research"))
            self.assertTrue(bool(ops["recommend_close"]))
            self.assertTrue(bool(coding["recommend_close"]))
            self.assertFalse(bool(research["recommend_close"]))
