from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cli_quality


class TestCliQuality(unittest.TestCase):
    def test_tool_version_strips_output(self) -> None:
        with patch.object(cli_quality, "_run_capture", return_value=(0, "x \n", "y \n")):
            r = cli_quality._tool_version(["x"], Path("."))
        self.assertEqual(r["code"], 0)
        self.assertEqual(r["out"], "x")
        self.assertEqual(r["err"], "y")

    def test_coverage_gate_run_failure(self) -> None:
        calls: list[list[str]] = []

        def fake_gate(cmd: list[str], cwd: Path):
            calls.append(cmd)
            return {"code": 2, "out": "no", "err": "bad"}

        with patch.object(cli_quality, "_gate", side_effect=fake_gate):
            r = cli_quality._coverage_gate("python", Path("."), fail_under=80)

        self.assertEqual(r["code"], 2)
        self.assertEqual(r["stage"], "run")
        self.assertTrue(calls)

    def test_coverage_gate_xml_failure_propagates(self) -> None:
        seq = [
            {"code": 0, "out": "ok", "err": ""},
            {"code": 0, "out": "report", "err": ""},
            {"code": 3, "out": "xml", "err": "xmlfail"},
        ]

        def fake_gate(cmd: list[str], cwd: Path):
            return seq.pop(0)

        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            with patch.object(cli_quality, "_gate", side_effect=fake_gate):
                r = cli_quality._coverage_gate("python", cwd, fail_under=80)

        self.assertEqual(r["stage"], "report")
        self.assertEqual(r["code"], 3)
        self.assertEqual(r["xml_code"], 3)

    def test_cmd_quality_summary_writes_report_without_running_gates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "q.json"
                args = argparse.Namespace(json=True, no_run=True, fail_under=80, write_report=str(out_path))

                def fake_run_capture(cmd: list[str], cwd: Path):
                    return 0, "ok", ""

                with patch.object(cli_quality, "_run_capture", side_effect=fake_run_capture):
                    code = cli_quality._cmd_quality_summary(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "quality_summary")
            self.assertEqual(payload["gates"], {})

    def test_cmd_quality_summary_includes_no_secrets_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                args = argparse.Namespace(json=True, no_run=False, fail_under=80, write_report=None)
                with (
                    patch.object(cli_quality, "_tool_version", return_value={"code": 0, "out": "ok", "err": ""}),
                    patch.object(cli_quality, "_no_secrets_gate", return_value={"code": 0, "out": "", "err": ""}) as sec_mock,
                    patch.object(cli_quality, "_gate", return_value={"code": 0, "out": "", "err": ""}),
                    patch.object(
                        cli_quality,
                        "_coverage_gate",
                        return_value={"code": 0, "stage": "report", "out": "", "err": "", "xml_code": 0, "xml_err": ""},
                    ),
                ):
                    code = cli_quality._cmd_quality_summary(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(sec_mock.called)

    def test_tracked_safety_gate_detects_vault_and_env(self) -> None:
        with patch.object(
            cli_quality,
            "_git_tracked_files",
            return_value={"code": 0, "files": ["vault/a.txt", ".env", "src/app.py"], "err": ""},
        ):
            result = cli_quality._tracked_safety_gate(Path("."))
        self.assertEqual(result["code"], 1)
        self.assertEqual(result["vault_tracked"], ["vault/a.txt"])
        self.assertEqual(result["env_like_tracked"], [".env"])

    def test_cmd_quality_public_readiness_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "public.json"
                args = argparse.Namespace(repo="egorKara/integrator", write_report=str(out_path), json=True)
                with (
                    patch.object(cli_quality, "_no_secrets_gate", return_value={"code": 0, "out": "", "err": ""}),
                    patch.object(
                        cli_quality,
                        "_tracked_safety_gate",
                        return_value={"code": 0, "vault_tracked": [], "env_like_tracked": [], "err": ""},
                    ),
                    patch.object(
                        cli_quality,
                        "_repo_visibility_gate",
                        return_value={
                            "code": 0,
                            "visibility": "public",
                            "repo": "egorKara/integrator",
                            "status": 200,
                            "error_kind": "",
                            "err": "",
                        },
                    ),
                    patch.object(
                        cli_quality,
                        "_repo_ruleset_gate",
                        return_value={
                            "code": 0,
                            "repo": "egorKara/integrator",
                            "ruleset_name": "integrator-main-protection",
                            "ruleset_id": 1,
                            "enforcement": "active",
                            "status": 200,
                            "error_kind": "",
                            "err": "",
                        },
                    ),
                ):
                    code = cli_quality._cmd_quality_public_readiness(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "public_repo_readiness")
            self.assertTrue(payload["ok"])
            self.assertIn("tracked_safety", payload["gates"])
            self.assertIn("repo_visibility", payload["gates"])
            self.assertIn("repo_ruleset", payload["gates"])

    def test_repo_visibility_gate_private_fails(self) -> None:
        class Resp:
            ok = True
            status = 200
            json = {"visibility": "private"}
            error_kind = None
            error = None

        with patch.object(cli_quality, "github_api_request", return_value=Resp()):
            result = cli_quality._repo_visibility_gate("egorKara/integrator", token="t")
        self.assertEqual(result["code"], 1)
        self.assertEqual(result["visibility"], "private")

    def test_repo_ruleset_gate_active_passes(self) -> None:
        class ListResp:
            ok = True
            status = 200
            json = [{"id": 7, "name": "integrator-main-protection", "enforcement": "active"}]
            error_kind = None
            error = None

        class DetailsResp:
            ok = True
            status = 200
            json = {
                "rules": [
                    {"type": "required_linear_history"},
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "strict_required_status_checks_policy": True,
                            "required_checks": [{"context": "ci / test"}],
                        },
                    },
                    {
                        "type": "pull_request",
                        "parameters": {
                            "required_approving_review_count": 2,
                            "dismiss_stale_reviews_on_push": True,
                            "require_code_owner_review": True,
                            "required_review_thread_resolution": True,
                        },
                    },
                ]
            }
            error_kind = None
            error = None

        with patch.object(cli_quality, "github_api_request", side_effect=[ListResp(), DetailsResp()]):
            result = cli_quality._repo_ruleset_gate("egorKara/integrator", token="t")
        self.assertEqual(result["code"], 0)
        self.assertEqual(result["ruleset_id"], 7)
        self.assertEqual(result["enforcement"], "active")

    def test_repo_ruleset_gate_missing_fails(self) -> None:
        class Resp:
            ok = True
            status = 200
            json = [{"id": 8, "name": "other", "enforcement": "active"}]
            error_kind = None
            error = None

        with patch.object(cli_quality, "github_api_request", return_value=Resp()):
            result = cli_quality._repo_ruleset_gate("egorKara/integrator", token="t")
        self.assertEqual(result["code"], 1)
        self.assertEqual(result["error_kind"], "ruleset_missing")

    def test_repo_ruleset_gate_policy_mismatch_fails(self) -> None:
        class ListResp:
            ok = True
            status = 200
            json = [{"id": 9, "name": "integrator-main-protection", "enforcement": "active"}]
            error_kind = None
            error = None

        class DetailsResp:
            ok = True
            status = 200
            json = {
                "rules": [
                    {"type": "required_linear_history"},
                    {
                        "type": "pull_request",
                        "parameters": {
                            "required_approving_review_count": 1,
                            "dismiss_stale_reviews_on_push": False,
                            "require_code_owner_review": False,
                            "required_review_thread_resolution": False,
                        },
                    },
                ]
            }
            error_kind = None
            error = None

        with patch.object(cli_quality, "github_api_request", side_effect=[ListResp(), DetailsResp()]):
            result = cli_quality._repo_ruleset_gate("egorKara/integrator", token="t")
        self.assertEqual(result["code"], 1)
        self.assertEqual(result["error_kind"], "ruleset_policy_mismatch")
        self.assertTrue(isinstance(result.get("policy_diff"), list))
        self.assertTrue(any(str(x.get("path", "")).startswith("rules.required_status_checks") for x in result["policy_diff"]))

    def test_public_readiness_generates_remediation_plan_when_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                report_path = Path(td) / "reports" / "public.json"
                plan_path = Path(td) / "reports" / "remediation.json"
                args = argparse.Namespace(
                    repo="egorKara/integrator",
                    write_report=str(report_path),
                    auto_remediation_plan=True,
                    probe_ruleset_payloads=True,
                    write_remediation_plan=str(plan_path),
                    json=True,
                )
                with (
                    patch.object(cli_quality, "_no_secrets_gate", return_value={"code": 0, "out": "", "err": ""}),
                    patch.object(
                        cli_quality,
                        "_tracked_safety_gate",
                        return_value={"code": 0, "vault_tracked": [], "env_like_tracked": [], "err": ""},
                    ),
                    patch.object(
                        cli_quality,
                        "_repo_visibility_gate",
                        return_value={
                            "code": 0,
                            "visibility": "public",
                            "repo": "egorKara/integrator",
                            "status": 200,
                            "error_kind": "",
                            "err": "",
                        },
                    ),
                    patch.object(
                        cli_quality,
                        "_repo_ruleset_gate",
                        return_value={
                            "code": 1,
                            "repo": "egorKara/integrator",
                            "ruleset_name": "integrator-main-protection",
                            "ruleset_id": 99,
                            "enforcement": "active",
                            "status": 200,
                            "policy_current": {},
                            "policy_desired": {},
                            "policy_diff": [{"path": "rules.required_status_checks.required_checks"}],
                            "ruleset_details": {
                                "target": "branch",
                                "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                                "rules": [
                                    {"type": "required_linear_history"},
                                    {
                                        "type": "pull_request",
                                        "parameters": {
                                            "required_approving_review_count": 2,
                                            "dismiss_stale_reviews_on_push": True,
                                            "require_code_owner_review": True,
                                            "required_review_thread_resolution": True,
                                        },
                                    },
                                ],
                            },
                            "error_kind": "ruleset_policy_mismatch",
                            "err": "rules.required_status_checks.required_checks",
                        },
                    ),
                ):
                    code = cli_quality._cmd_quality_public_readiness(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 1)
            self.assertTrue(report_path.exists())
            self.assertTrue(plan_path.exists())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["remediation"]["enabled"])
            self.assertTrue(payload["remediation"]["generated"])
            self.assertTrue(payload["remediation"]["probe_enabled"])
            self.assertTrue(payload["remediation"]["probe_generated"])
            self.assertEqual(payload["artifacts"]["remediation_plan_json"], str(plan_path))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertTrue(isinstance(plan.get("candidate_payloads"), list))
            self.assertTrue(isinstance(plan.get("probe"), dict))
            self.assertTrue(str(plan["probe"].get("recommended_candidate_id", "")))

    def test_probe_ruleset_candidate_payloads_remote(self) -> None:
        candidates = [
            {
                "id": "c1",
                "label": "candidate one",
                "payload": {"name": "rs", "target": "branch", "enforcement": "active", "rules": [{"type": "pull_request"}]},
            }
        ]

        class CreateResp:
            ok = True
            status = 201
            json = {"id": 555}
            error_kind = None
            error = None

        class DeleteResp:
            ok = True
            status = 204
            json: dict[str, object] = {}
            error_kind = None
            error = None

        with (
            patch.object(
                cli_quality,
                "_adapter_variants_for_payload",
                return_value=[{"adapter_id": "a1", "adapter_kind": "minimize_fields", "payload": candidates[0]["payload"]}],
            ),
            patch.object(cli_quality, "github_api_request", side_effect=[CreateResp(), DeleteResp()]),
        ):
            result = cli_quality._probe_ruleset_candidate_payloads_remote("egorKara/integrator", "t", candidates)
        self.assertEqual(result["mode"], "remote_temp_ruleset")
        self.assertEqual(result["mutation"], "temporary_create_delete")
        self.assertEqual(result["recommended_candidate_id"], "c1")
        self.assertTrue(result["results"][0]["supported"])
        self.assertTrue(result["results"][0]["cleanup_ok"])

    def test_public_readiness_remote_probe_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                report_path = Path(td) / "reports" / "public.json"
                plan_path = Path(td) / "reports" / "remediation.json"
                args = argparse.Namespace(
                    repo="egorKara/integrator",
                    write_report=str(report_path),
                    auto_remediation_plan=True,
                    probe_ruleset_payloads=True,
                    probe_on_remote=True,
                    write_remediation_plan=str(plan_path),
                    json=True,
                )
                with (
                    patch.object(cli_quality, "_no_secrets_gate", return_value={"code": 0, "out": "", "err": ""}),
                    patch.object(
                        cli_quality,
                        "_tracked_safety_gate",
                        return_value={"code": 0, "vault_tracked": [], "env_like_tracked": [], "err": ""},
                    ),
                    patch.object(
                        cli_quality,
                        "_repo_visibility_gate",
                        return_value={
                            "code": 0,
                            "visibility": "public",
                            "repo": "egorKara/integrator",
                            "status": 200,
                            "error_kind": "",
                            "err": "",
                        },
                    ),
                    patch.object(
                        cli_quality,
                        "_repo_ruleset_gate",
                        return_value={
                            "code": 1,
                            "repo": "egorKara/integrator",
                            "ruleset_name": "integrator-main-protection",
                            "ruleset_id": 99,
                            "enforcement": "active",
                            "status": 200,
                            "policy_current": {},
                            "policy_desired": {},
                            "policy_diff": [{"path": "rules.required_status_checks.required_checks"}],
                            "ruleset_details": {"target": "branch", "conditions": {}, "rules": [{"type": "pull_request"}]},
                            "error_kind": "ruleset_policy_mismatch",
                            "err": "rules.required_status_checks.required_checks",
                        },
                    ),
                    patch.object(
                        cli_quality,
                        "_probe_ruleset_candidate_payloads_remote",
                        return_value={"kind": "ruleset_probe_result", "mode": "remote_temp_ruleset", "results": []},
                    ),
                ):
                    code = cli_quality._cmd_quality_public_readiness(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 1)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["remediation"]["probe_on_remote"])
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan["probe"]["mode"], "remote_temp_ruleset")

    def test_apply_approved_candidate_requires_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = Path(td) / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "kind": "ruleset_remediation_plan",
                        "ruleset_id": 1,
                        "candidate_payloads": [{"id": "c1", "payload": {"name": "x", "target": "branch", "rules": []}}],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                repo="egorKara/integrator",
                plan=str(plan_path),
                candidate_id="c1",
                confirm="NOPE",
                write_report=None,
                json=True,
            )
            code = cli_quality._cmd_quality_apply_approved_candidate(args)
            self.assertEqual(code, 2)

    def test_apply_approved_candidate_applies_selected_candidate_and_runs_post_check(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                plan_path = Path(td) / "plan.json"
                candidate_payload = {
                    "name": "integrator-main-protection",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                    "rules": [{"type": "required_linear_history"}],
                }
                plan_path.write_text(
                    json.dumps(
                        {
                            "kind": "ruleset_remediation_plan",
                            "ruleset_id": 123,
                            "candidate_payloads": [{"id": "c1", "payload": candidate_payload}],
                        }
                    ),
                    encoding="utf-8",
                )
                out_path = Path(td) / "reports" / "apply.json"
                args = argparse.Namespace(
                    repo="egorKara/integrator",
                    plan=str(plan_path),
                    candidate_id="c1",
                    confirm="APPLY",
                    write_report=str(out_path),
                    json=True,
                )

                class ApplyResp:
                    ok = True
                    status = 200
                    json = {"id": 123}
                    error_kind = None
                    error = None

                with (
                    patch.object(cli_quality, "load_github_token", return_value="t"),
                    patch.object(cli_quality, "_collect_public_readiness_gates", return_value={"repo_ruleset": {"code": 0}}),
                    patch.object(cli_quality, "github_api_request", return_value=ApplyResp()) as req_mock,
                ):
                    code = cli_quality._cmd_quality_apply_approved_candidate(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            req_mock.assert_called_once()
            called_args, called_kwargs = req_mock.call_args
            self.assertEqual(called_args[0], "PUT")
            self.assertIn("/repos/egorKara/integrator/rulesets/123", called_args[1])
            self.assertEqual(called_kwargs["payload"], candidate_payload)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["candidate_id"], "c1")
            self.assertTrue(payload["post_check_ok"])

    def test_apply_approved_candidate_fails_without_compatible_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = Path(td) / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "kind": "ruleset_remediation_plan",
                        "ruleset_id": 123,
                        "candidate_payloads": [{"id": "c1", "payload": {"name": "x", "target": "branch", "rules": []}}],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                repo="egorKara/integrator",
                plan=str(plan_path),
                candidate_id="c1",
                use_compatible_payload=True,
                confirm="APPLY",
                write_report=None,
                json=True,
            )
            with patch.object(cli_quality, "load_github_token", return_value="t"):
                code = cli_quality._cmd_quality_apply_approved_candidate(args)
            self.assertEqual(code, 2)

    def test_apply_approved_candidate_uses_compatible_payload_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                plan_path = Path(td) / "plan.json"
                compatible_payload = {
                    "name": "integrator-main-protection",
                    "target": "branch",
                    "enforcement": "active",
                    "rules": [{"type": "required_linear_history"}],
                }
                plan_path.write_text(
                    json.dumps(
                        {
                            "kind": "ruleset_remediation_plan",
                            "ruleset_id": 123,
                            "candidate_payloads": [{"id": "c1", "payload": {"name": "x", "target": "branch", "rules": []}}],
                            "compatible_payload": {"candidate_id": "c1", "payload": compatible_payload},
                        }
                    ),
                    encoding="utf-8",
                )
                out_path = Path(td) / "reports" / "apply_compatible.json"
                args = argparse.Namespace(
                    repo="egorKara/integrator",
                    plan=str(plan_path),
                    candidate_id="c1",
                    use_compatible_payload=True,
                    confirm="APPLY",
                    write_report=str(out_path),
                    json=True,
                )

                class ApplyResp:
                    ok = True
                    status = 200
                    json = {"id": 123}
                    error_kind = None
                    error = None

                with (
                    patch.object(cli_quality, "load_github_token", return_value="t"),
                    patch.object(cli_quality, "_collect_public_readiness_gates", return_value={"repo_ruleset": {"code": 0}}),
                    patch.object(cli_quality, "github_api_request", return_value=ApplyResp()) as req_mock,
                ):
                    code = cli_quality._cmd_quality_apply_approved_candidate(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 0)
            called_args, called_kwargs = req_mock.call_args
            self.assertEqual(called_args[0], "PUT")
            self.assertEqual(called_kwargs["payload"], compatible_payload)

    def test_projects_migration_readiness_recommends_projects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                report_path = Path(td) / "reports" / "projects_ready.json"
                args = argparse.Namespace(
                    repo="egorKara/integrator",
                    issues_threshold=2,
                    pulls_threshold=1,
                    stale_threshold=1,
                    stale_days=7,
                    triage_coverage_threshold=0.6,
                    recommendation_score_threshold=2,
                    write_report=str(report_path),
                    json=True,
                )
                old_issue = {
                    "number": 1,
                    "updated_at": "2026-01-01T00:00:00Z",
                    "labels": [{"name": "remote"}],
                }
                triaged_issue = {
                    "number": 2,
                    "updated_at": "2026-01-01T00:00:00Z",
                    "labels": [{"name": "priority:p1"}],
                }
                pull = {"number": 3, "updated_at": "2026-01-01T00:00:00Z"}
                with patch.object(
                    cli_quality,
                    "_github_list_all",
                    side_effect=[{"ok": True, "items": [old_issue, triaged_issue]}, {"ok": True, "items": [pull]}],
                ):
                    code = cli_quality._cmd_quality_projects_migration_readiness(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["recommend_projects_migration"])
            self.assertTrue(payload["metrics"]["open_issues"] >= 2)

    def test_projects_migration_readiness_api_failure(self) -> None:
        args = argparse.Namespace(
            repo="egorKara/integrator",
            issues_threshold=6,
            pulls_threshold=3,
            stale_threshold=3,
            stale_days=7,
            triage_coverage_threshold=0.6,
            recommendation_score_threshold=2,
            write_report=None,
            json=True,
        )
        with patch.object(
            cli_quality,
            "_github_list_all",
            side_effect=[{"ok": False, "status": 500, "items": []}, {"ok": True, "items": []}],
        ):
            code = cli_quality._cmd_quality_projects_migration_readiness(args)
        self.assertEqual(code, 1)

    def test_mcp_tools_inventory_discovers_from_registry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                root = Path(td) / "LocalAI" / "assistant"
                root.mkdir(parents=True, exist_ok=True)
                (root / "mcp_server.py").write_text("print('ok')\n", encoding="utf-8")
                registry = [
                    {
                        "name": "localai-assistant",
                        "root": "LocalAI/assistant",
                        "entrypoint": "python LocalAI/assistant/mcp_server.py",
                    }
                ]
                Path(td, "registry.json").write_text(json.dumps(registry), encoding="utf-8")
                out_path = Path(td) / "reports" / "mcp_inventory.json"
                args = argparse.Namespace(roots=[], write_report=str(out_path), json=True)
                code = cli_quality._cmd_quality_mcp_tools_inventory(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "mcp_tools_inventory")
            self.assertEqual(payload["mcp_servers_found"], 1)
            self.assertTrue(payload["servers"][0]["mcp_server"].endswith("mcp_server.py"))

    def test_mcp_tools_inventory_supports_extra_roots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                extra = Path(td) / "x" / "assistant"
                extra.mkdir(parents=True, exist_ok=True)
                (extra / "mcp_server.py").write_text("print('ok')\n", encoding="utf-8")
                args = argparse.Namespace(roots=[str(extra)], write_report=None, json=True)
                code = cli_quality._cmd_quality_mcp_tools_inventory(args)
            finally:
                os.chdir(prev)
            self.assertEqual(code, 0)

    def test_cmd_quality_github_snapshot_invalid_repo(self) -> None:
        args = argparse.Namespace(repo="bad-slug", state="open", write_report=None, json=True)
        code = cli_quality._cmd_quality_github_snapshot(args)
        self.assertEqual(code, 2)

    def test_cmd_quality_github_snapshot_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "snap.json"
                args = argparse.Namespace(repo="egorKara/integrator", state="open", write_report=str(out_path), json=True)

                def fake_list(url: str, token: str | None):
                    if "/issues?" in url:
                        return {
                            "ok": True,
                            "status": 200,
                            "error": "",
                            "items": [
                                {"number": 1, "title": "Issue", "state": "open", "updated_at": "2026-01-01", "html_url": "u1"},
                                {
                                    "number": 2,
                                    "title": "PR-like in issues",
                                    "state": "open",
                                    "updated_at": "2026-01-01",
                                    "html_url": "u2",
                                    "pull_request": {"url": "x"},
                                },
                            ],
                        }
                    return {
                        "ok": True,
                        "status": 200,
                        "error": "",
                        "items": [
                            {
                                "number": 3,
                                "title": "PR",
                                "state": "open",
                                "updated_at": "2026-01-02",
                                "html_url": "u3",
                                "draft": False,
                            }
                        ],
                    }

                with (
                    patch.object(cli_quality, "_github_list_all", side_effect=fake_list),
                    patch.object(cli_quality, "load_github_token", return_value="t"),
                ):
                    code = cli_quality._cmd_quality_github_snapshot(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "github_snapshot")
            self.assertEqual(payload["issues_open_count"], 1)
            self.assertEqual(payload["pulls_open_count"], 1)
            self.assertIn("artifacts", payload)
            artifacts = payload["artifacts"]
            self.assertTrue(Path(artifacts["report_json"]).exists())
            self.assertTrue(Path(artifacts["report_md"]).exists())

    def test_github_list_all_handles_pagination(self) -> None:
        class Resp:
            def __init__(self, ok: bool, status: int, json_payload):
                self.ok = ok
                self.status = status
                self.json = json_payload
                self.error = None

        seq = [
            Resp(True, 200, [{"n": 1}] * 100),
            Resp(True, 200, [{"n": 2}]),
        ]
        with patch.object(cli_quality, "github_api_request", side_effect=lambda *args, **kwargs: seq.pop(0)):
            result = cli_quality._github_list_all("https://api.github.com/repos/a/b/issues?state=open", "t")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["items"]), 101)

    def test_github_list_all_handles_error(self) -> None:
        class Resp:
            ok = False
            status = 403
            json = None
            error = "denied"

        with patch.object(cli_quality, "github_api_request", return_value=Resp()):
            result = cli_quality._github_list_all("https://api.github.com/repos/a/b/issues?state=open", "t")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 403)

    def test_cmd_quality_github_snapshot_returns_error_on_api_failure(self) -> None:
        args = argparse.Namespace(repo="egorKara/integrator", state="open", write_report=None, json=True)
        with patch.object(cli_quality, "_github_list_all", return_value={"ok": False, "status": 500, "error": "e", "items": []}):
            code = cli_quality._cmd_quality_github_snapshot(args)
        self.assertEqual(code, 1)
