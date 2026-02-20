import io
import json
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest import mock

from agent_memory_client import HttpResult, _join_url, _read_text, memory_write, memory_write_file


class AgentMemoryClientTests(unittest.TestCase):
    def test_join_url_requires_base(self) -> None:
        with self.assertRaises(ValueError):
            _join_url("", "/x")
        self.assertEqual(_join_url("http://a", "x"), "http://a/x")
        self.assertEqual(_join_url("http://a/", "/x"), "http://a/x")

    def test_read_text_truncates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.txt"
            p.write_text("hello", encoding="utf-8")
            self.assertEqual(_read_text(str(p), max_chars=3), "hel")
            self.assertEqual(_read_text(str(p), max_chars=None), "hello")

    def test_memory_write_builds_payload_and_calls_http(self) -> None:
        def fake_http(
            method: str,
            url: str,
            payload: dict[str, object] | None,
            auth_token: str | None,
            timeout_sec: float = 10.0,
        ) -> HttpResult:
            self.assertEqual(method, "POST")
            self.assertTrue(url.endswith("/agent/memory/write"))
            assert payload is not None
            self.assertEqual(payload.get("summary"), "s")
            self.assertEqual(payload.get("kind"), "event")
            self.assertEqual(payload.get("tags"), ["t"])
            return HttpResult(status=200, body=b"{}", json={"record": {"id": "1"}})

        with mock.patch("agent_memory_client._http_json", side_effect=fake_http):
            res = memory_write("http://127.0.0.1:8011", "s", "c", tags=["t"])
        self.assertEqual(res.status, 200)

    def test_memory_write_file_chunks_and_metadata(self) -> None:
        calls: list[tuple[str, str, str, dict[str, object]]] = []

        def fake_write(base_url: str, summary: str, content: str, *, auth_token: str | None = None, **kwargs: object) -> HttpResult:
            calls.append((base_url, summary, content, dict(kwargs)))
            return HttpResult(status=201, body=b"{}", json={"record": {"id": summary}})

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.txt"
            p.write_text("abcd", encoding="utf-8")
            with mock.patch("agent_memory_client.memory_write", side_effect=fake_write):
                res = memory_write_file("http://x", "S", str(p), chunk_size=2, metadata={"k": "v"})

        self.assertEqual(len(res), 2)
        self.assertEqual(calls[0][1], "S (part 1/2)")
        self.assertEqual(calls[1][1], "S (part 2/2)")
        self.assertEqual(calls[0][2], "ab")
        self.assertEqual(calls[1][2], "cd")
        meta0 = calls[0][3].get("metadata", {})
        assert isinstance(meta0, dict)
        self.assertEqual(meta0.get("k"), "v")
        self.assertEqual(meta0.get("chunk_index"), 1)
        self.assertEqual(meta0.get("chunk_total"), 2)

    def test_http_error_parses_json(self) -> None:
        err_body = json.dumps({"error": "bad"}).encode("utf-8")
        fp = io.BytesIO(err_body)
        http_err = urllib.error.HTTPError(
            url="http://x",
            code=400,
            msg="bad",
            hdrs=Message(),
            fp=fp,
        )

        try:
            with mock.patch("urllib.request.urlopen", side_effect=http_err):
                from agent_memory_client import _http_json

                res = _http_json("POST", "http://x", {"a": 1}, auth_token=None)
            self.assertEqual(res.status, 400)
            self.assertIsInstance(res.json, dict)
        finally:
            try:
                http_err.close()
            except Exception:
                pass
            fp.close()
