import io
import json
import os
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest import mock

from github_api import (
    _classify_github_http_error,
    _parse_env_kv,
    default_github_token_file,
    github_api_headers,
    github_api_request,
    load_github_token,
)


class _DummyResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_DummyResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class GitHubApiTests(unittest.TestCase):
    def test_default_github_token_file_uses_integrator_secrets_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.dict(os.environ, {"INTEGRATOR_SECRETS_DIR": td}, clear=True):
                p = default_github_token_file()
        self.assertEqual(p.name, "github_token.txt")
        self.assertEqual(p.parent, Path(td).resolve())

    def test_load_github_token_returns_none_when_explicit_file_unreadable(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN_FILE": "X:/missing/token.txt"}, clear=True):
            self.assertIsNone(load_github_token())

    def test_parse_env_kv_skips_invalid_and_unquotes(self) -> None:
        data = """
        # comment
        GOOD_A=aaa
        GOOD_B="bbb"
        GOOD_C='ccc'
        =bad
        NOEQ
        """
        parsed = _parse_env_kv(data)
        self.assertEqual(parsed.get("GOOD_A"), "aaa")
        self.assertEqual(parsed.get("GOOD_B"), "bbb")
        self.assertEqual(parsed.get("GOOD_C"), "ccc")
        self.assertNotIn("", parsed)

    def test_github_api_headers_without_token(self) -> None:
        headers = github_api_headers(None)
        self.assertIn("Accept", headers)
        self.assertIn("X-GitHub-Api-Version", headers)
        self.assertNotIn("Authorization", headers)

    def test_load_github_token_from_env(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "  tok  "}, clear=True):
            self.assertEqual(load_github_token(), "tok")

    def test_load_github_token_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "token.txt"
            p.write_text(" tok\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"GITHUB_TOKEN_FILE": str(p)}, clear=True):
                self.assertEqual(load_github_token(), "tok")

    def test_load_github_token_from_dotenv(self) -> None:
        import github_api

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / ".env").write_text("GITHUB_TOKEN=tok\n", encoding="utf-8")
            fake_module_path = td_path / "github_api.py"
            with mock.patch.object(github_api, "__file__", str(fake_module_path)):
                with mock.patch.dict(os.environ, {"USERPROFILE": td}, clear=True):
                    self.assertEqual(load_github_token(), "tok")

    def test_env_overrides_dotenv(self) -> None:
        import github_api

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / ".env").write_text("GITHUB_TOKEN=filetok\n", encoding="utf-8")
            fake_module_path = td_path / "github_api.py"
            with mock.patch.object(github_api, "__file__", str(fake_module_path)):
                with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "envtok", "USERPROFILE": td}, clear=True):
                    self.assertEqual(load_github_token(), "envtok")

    def test_request_sets_authorization_header(self) -> None:
        def fake_urlopen(req: object, timeout: float = 0.0) -> _DummyResponse:
            assert hasattr(req, "header_items")
            items = {k.lower(): v for k, v in req.header_items()}  # type: ignore[attr-defined]
            self.assertEqual(items.get("authorization"), "Bearer tok")
            self.assertEqual(items.get("accept"), "application/vnd.github+json")
            self.assertEqual(items.get("x-github-api-version"), "2022-11-28")
            return _DummyResponse(200, b'{"a": 1}')

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = github_api_request("GET", "https://api.github.com/repos/o/r", token="tok")
        self.assertTrue(res.ok)
        self.assertEqual(res.status, 200)
        self.assertEqual(res.json, {"a": 1})

    def test_404_without_token_classified_as_auth_missing(self) -> None:
        err_body = json.dumps({"message": "Not Found"}).encode("utf-8")
        fp = io.BytesIO(err_body)
        http_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/o/r",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=fp,
        )
        try:
            with mock.patch("urllib.request.urlopen", side_effect=http_err):
                res = github_api_request("GET", "https://api.github.com/repos/o/r", token=None)
            self.assertFalse(res.ok)
            self.assertEqual(res.status, 404)
            self.assertEqual(res.error_kind, "auth_missing")
        finally:
            try:
                http_err.close()
            except Exception:
                pass
            fp.close()

    def test_404_with_token_classified_as_not_found_or_authz(self) -> None:
        err_body = json.dumps({"message": "Not Found"}).encode("utf-8")
        fp = io.BytesIO(err_body)
        http_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/o/r",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=fp,
        )
        try:
            with mock.patch("urllib.request.urlopen", side_effect=http_err):
                res = github_api_request("GET", "https://api.github.com/repos/o/r", token="tok")
            self.assertFalse(res.ok)
            self.assertEqual(res.status, 404)
            self.assertEqual(res.error_kind, "not_found_or_authz")
        finally:
            try:
                http_err.close()
            except Exception:
                pass
            fp.close()

    def test_401_with_token_classified_as_auth_error(self) -> None:
        err_body = json.dumps({"message": "Bad credentials"}).encode("utf-8")
        fp = io.BytesIO(err_body)
        http_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/o/r",
            code=401,
            msg="Unauthorized",
            hdrs=Message(),
            fp=fp,
        )
        try:
            with mock.patch("urllib.request.urlopen", side_effect=http_err):
                res = github_api_request("GET", "https://api.github.com/repos/o/r", token="tok")
            self.assertFalse(res.ok)
            self.assertEqual(res.status, 401)
            self.assertEqual(res.error_kind, "auth_error")
        finally:
            try:
                http_err.close()
            except Exception:
                pass
            fp.close()

    def test_403_plan_limit_classified_as_feature_unavailable_plan(self) -> None:
        err_body = json.dumps(
            {"message": "Upgrade to GitHub Pro or make this repository public to enable this feature."}
        ).encode("utf-8")
        fp = io.BytesIO(err_body)
        http_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/o/r/branches/main/protection",
            code=403,
            msg="Forbidden",
            hdrs=Message(),
            fp=fp,
        )
        try:
            with mock.patch("urllib.request.urlopen", side_effect=http_err):
                res = github_api_request(
                    "PUT",
                    "https://api.github.com/repos/o/r/branches/main/protection",
                    token="tok",
                    payload={"required_status_checks": {"strict": True, "contexts": ["ci / test"]}},
                )
            self.assertFalse(res.ok)
            self.assertEqual(res.status, 403)
            self.assertEqual(res.error_kind, "feature_unavailable_plan")
        finally:
            try:
                http_err.close()
            except Exception:
                pass
            fp.close()

    def test_request_payload_sets_content_type(self) -> None:
        def fake_urlopen(req: object, timeout: float = 0.0) -> _DummyResponse:
            assert hasattr(req, "header_items")
            assert hasattr(req, "data")
            items = {k.lower(): v for k, v in req.header_items()}  # type: ignore[attr-defined]
            self.assertEqual(items.get("content-type"), "application/json")
            raw = req.data  # type: ignore[attr-defined]
            self.assertIsInstance(raw, bytes)
            payload = json.loads(raw.decode("utf-8"))
            self.assertEqual(payload["x"], 1)
            return _DummyResponse(201, b'{"ok":true}')

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = github_api_request("POST", "https://api.github.com/repos/o/r", token="tok", payload={"x": 1})
        self.assertTrue(res.ok)
        self.assertEqual(res.status, 201)

    def test_request_network_error_classified(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
            res = github_api_request("GET", "https://api.github.com/repos/o/r", token=None)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, 0)
        self.assertEqual(res.error_kind, "network_error")

    def test_classify_http_error_default(self) -> None:
        kind, msg = _classify_github_http_error(status=500, token_present=True, body_message="")
        self.assertEqual(kind, "http_error")
        self.assertIn("500", msg)
