import unittest
from unittest import mock

from github_api import GitHubApiResult
from github_issues import issue_close, issue_comment, issue_create, parse_repo_slug, repo_access


class GitHubIssuesTests(unittest.TestCase):
    def test_parse_repo_slug_owner_repo(self) -> None:
        self.assertEqual(parse_repo_slug("a/b"), ("a", "b"))

    def test_parse_repo_slug_git_url(self) -> None:
        self.assertEqual(parse_repo_slug("https://github.com/a/b.git"), ("a", "b"))
        self.assertEqual(parse_repo_slug("git@github.com:a/b.git"), ("a", "b"))

    def test_repo_access_uses_repos_endpoint(self) -> None:
        def fake(method: str, url: str, *, token: str | None, payload: dict[str, object] | None = None, **_: object) -> GitHubApiResult:
            self.assertEqual(method, "GET")
            self.assertEqual(url, "https://api.github.com/repos/o/r")
            self.assertEqual(token, "t")
            self.assertIsNone(payload)
            return GitHubApiResult(ok=True, status=200, json={"id": 1})

        with mock.patch("github_issues.github_api_request", side_effect=fake):
            res = repo_access("o", "r", token="t")
        self.assertTrue(res.ok)

    def test_issue_create_payload(self) -> None:
        def fake(method: str, url: str, *, token: str | None, payload: dict[str, object] | None = None, **_: object) -> GitHubApiResult:
            self.assertEqual(method, "POST")
            self.assertEqual(url, "https://api.github.com/repos/o/r/issues")
            assert payload is not None
            self.assertEqual(payload.get("title"), "T")
            self.assertEqual(payload.get("body"), "B")
            self.assertEqual(payload.get("labels"), ["tracked"])
            return GitHubApiResult(ok=True, status=201, json={"number": 7})

        with mock.patch("github_issues.github_api_request", side_effect=fake):
            res = issue_create("o", "r", token="t", title="T", body="B", labels=["tracked"])
        self.assertTrue(res.ok)

    def test_issue_comment_payload(self) -> None:
        def fake(method: str, url: str, *, token: str | None, payload: dict[str, object] | None = None, **_: object) -> GitHubApiResult:
            self.assertEqual(method, "POST")
            self.assertEqual(url, "https://api.github.com/repos/o/r/issues/7/comments")
            assert payload is not None
            self.assertEqual(payload.get("body"), "X")
            return GitHubApiResult(ok=True, status=201, json={"id": 1})

        with mock.patch("github_issues.github_api_request", side_effect=fake):
            res = issue_comment("o", "r", token="t", number=7, body="X")
        self.assertTrue(res.ok)

    def test_issue_close_payload(self) -> None:
        def fake(method: str, url: str, *, token: str | None, payload: dict[str, object] | None = None, **_: object) -> GitHubApiResult:
            self.assertEqual(method, "PATCH")
            self.assertEqual(url, "https://api.github.com/repos/o/r/issues/7")
            assert payload is not None
            self.assertEqual(payload.get("state"), "closed")
            return GitHubApiResult(ok=True, status=200, json={"state": "closed"})

        with mock.patch("github_issues.github_api_request", side_effect=fake):
            res = issue_close("o", "r", token="t", number=7)
        self.assertTrue(res.ok)

