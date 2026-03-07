from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from github_api import GitHubApiResult
from tools import apply_branch_protection


class ApplyBranchProtectionTests(unittest.TestCase):
    def test_private_repo_returns_precondition_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "egorKara/integrator"}, clear=False):
                    with (
                        mock.patch("github_api.load_github_token", return_value="tok"),
                        mock.patch(
                            "github_api.github_api_request",
                            return_value=GitHubApiResult(ok=True, status=200, json={"visibility": "private"}),
                        ),
                    ):
                        code = apply_branch_protection.main(["apply_branch_protection.py"])
            finally:
                os.chdir(prev)

            self.assertEqual(code, 1)
            reports = list((Path(td) / "reports").glob("branch_protection_apply_*.json"))
            self.assertEqual(len(reports), 1)
            payload = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["checks"]["precondition_visibility"]["error_kind"], "feature_unavailable_plan")

    def test_check_only_keeps_success_for_private_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "egorKara/integrator"}, clear=False):
                    with (
                        mock.patch("github_api.load_github_token", return_value="tok"),
                        mock.patch(
                            "github_api.github_api_request",
                            return_value=GitHubApiResult(ok=True, status=200, json={"visibility": "private"}),
                        ),
                    ):
                        code = apply_branch_protection.main(["apply_branch_protection.py", "--check-only"])
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)

    def test_public_repo_uses_single_protection_endpoint_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                calls: list[tuple[str, str, dict | None]] = []

                def fake_request(method: str, url: str, *, token: str | None, payload=None, timeout_sec: float = 20.0):
                    calls.append((method, url, payload))
                    if method == "GET" and url.endswith("/repos/egorKara/integrator"):
                        return GitHubApiResult(ok=True, status=200, json={"visibility": "public"})
                    if method == "GET" and url.endswith("/rulesets"):
                        return GitHubApiResult(ok=True, status=200, json={})
                    if method == "POST" and url.endswith("/rulesets"):
                        return GitHubApiResult(ok=True, status=201, json={"id": 7, "name": "integrator-main-protection"})
                    return GitHubApiResult(ok=False, status=500, json={"message": "unexpected"})

                with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "egorKara/integrator"}, clear=False):
                    with (
                        mock.patch("github_api.load_github_token", return_value="tok"),
                        mock.patch("github_api.github_api_request", side_effect=fake_request),
                    ):
                        code = apply_branch_protection.main(["apply_branch_protection.py"])
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[1][0], "GET")
            self.assertEqual(calls[2][0], "POST")

    def test_ruleset_fallback_when_legacy_protection_api_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                calls: list[tuple[str, str]] = []

                def fake_request(method: str, url: str, *, token: str | None, payload=None, timeout_sec: float = 20.0):
                    calls.append((method, url))
                    if method == "GET" and url.endswith("/repos/egorKara/integrator"):
                        return GitHubApiResult(ok=True, status=200, json={"visibility": "public"})
                    if method == "GET" and url.endswith("/rulesets"):
                        return GitHubApiResult(ok=True, status=200, json={})
                    if method == "POST" and url.endswith("/rulesets"):
                        return GitHubApiResult(ok=True, status=201, json={"id": 1, "name": "integrator-main-protection"})
                    return GitHubApiResult(ok=False, status=500, json={"message": "unexpected"})

                with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "egorKara/integrator"}, clear=False):
                    with (
                        mock.patch("github_api.load_github_token", return_value="tok"),
                        mock.patch("github_api.github_api_request", side_effect=fake_request),
                    ):
                        code = apply_branch_protection.main(["apply_branch_protection.py"])
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(any(x[0] == "POST" and x[1].endswith("/rulesets") for x in calls))
