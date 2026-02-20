import io
import json
import os
import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest import mock
from uuid import uuid4

from tools.lm_studio_sidecar import run


@contextmanager
def case_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".tmp_sidecar_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    prev = os.getcwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(prev)
        shutil.rmtree(root, ignore_errors=True)


class LmStudioSidecarTests(unittest.TestCase):
    def test_dry_run_writes_md(self) -> None:
        with case_dir() as root:
            inp = root / "a.json"
            inp.write_text("{}", encoding="utf-8")
            out = run(
                mode="recommendations",
                inputs=[inp],
                output_dir=root / "reports",
                base_url="http://127.0.0.1:1234",
                model="local-model",
                max_chars=1000,
                allow_sensitive=False,
                write_response_json=False,
                dry_run=True,
            )
            self.assertEqual(len(out.outputs), 1)
            self.assertTrue(Path(out.outputs[0]).exists())

    def test_sensitive_block(self) -> None:
        with case_dir() as root:
            inp = root / ".env"
            inp.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                run(
                    mode="tests",
                    inputs=[inp],
                    output_dir=root / "reports",
                    base_url="http://127.0.0.1:1234",
                    model="local-model",
                    max_chars=1000,
                    allow_sensitive=False,
                    write_response_json=False,
                    dry_run=True,
                )

    def test_call_writes_md_from_response(self) -> None:
        with case_dir() as root:
            inp = root / "a.json"
            inp.write_text('{"k":"v"}', encoding="utf-8")

            resp = {"choices": [{"message": {"content": "# OK\n\ntext\n"}}]}
            raw = json.dumps(resp).encode("utf-8")

            class FakeResp(io.BytesIO):
                status = 200

                def __enter__(self) -> "FakeResp":
                    return self

                def __exit__(self, exc_type, exc, tb) -> None:
                    return None

            with mock.patch("urllib.request.urlopen", return_value=FakeResp(raw)):
                out = run(
                    mode="ci-triage",
                    inputs=[inp],
                    output_dir=root / "reports",
                    base_url="http://127.0.0.1:1234",
                    model="local-model",
                    max_chars=1000,
                    allow_sensitive=False,
                    write_response_json=True,
                    dry_run=False,
                )
            self.assertEqual(len(out.outputs), 1)
            md_path = Path(out.outputs[0])
            self.assertTrue(md_path.exists())
            self.assertIn("# OK", md_path.read_text(encoding="utf-8"))
