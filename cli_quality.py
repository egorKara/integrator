from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from github_api import github_api_request, load_github_token
from github_issues import parse_repo_slug
from utils import _print_json, _print_tab, _run_capture, _write_text_atomic


def _tool_version(cmd: list[str], cwd: Path) -> dict[str, Any]:
    code, out, err = _run_capture(cmd, cwd)
    return {"code": code, "out": out.strip(), "err": err.strip()}


def _gate(cmd: list[str], cwd: Path) -> dict[str, Any]:
    code, out, err = _run_capture(cmd, cwd)
    return {"code": code, "out": out.strip(), "err": err.strip()}


def _coverage_gate(python_cmd: str, cwd: Path, fail_under: int) -> dict[str, Any]:
    reports_dir = (cwd / "reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    run = _gate(
        [python_cmd, "-m", "coverage", "run", "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"],
        cwd,
    )
    if run["code"] != 0:
        return {"code": int(run["code"]), "stage": "run", "out": run["out"], "err": run["err"]}

    report = _gate(
        [python_cmd, "-m", "coverage", "report", "-m", "--fail-under", str(int(fail_under))],
        cwd,
    )
    xml = _gate([python_cmd, "-m", "coverage", "xml", "-o", str(reports_dir / "coverage.xml")], cwd)

    code = int(report["code"]) if int(report["code"]) != 0 else int(xml["code"])
    return {
        "code": code,
        "stage": "report",
        "out": report["out"],
        "err": report["err"],
        "xml_code": int(xml["code"]),
        "xml_err": xml["err"],
    }


def _no_secrets_gate(python_cmd: str, cwd: Path) -> dict[str, Any]:
    raw = _gate([python_cmd, "guardrails.py", "--json", "--scan-tracked", "--scan-reports"], cwd)
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(str(raw.get("out", "") or "{}"))
    except json.JSONDecodeError:
        payload = {}
    checks = payload.get("checks", []) if isinstance(payload, dict) else []
    secret_checks = [
        c for c in checks if isinstance(c, dict) and str(c.get("name", "")).startswith("secret_scan")
    ]
    has_secret_problem = any(str(c.get("status", "")) != "ok" for c in secret_checks)
    return {
        "code": 1 if has_secret_problem else 0,
        "out": raw.get("out", ""),
        "err": raw.get("err", ""),
        "raw_code": int(raw.get("code", 0)),
    }


def _git_tracked_files(cwd: Path) -> dict[str, Any]:
    code, out, err = _run_capture(["git", "ls-files"], cwd)
    files = [line.strip() for line in out.splitlines() if line.strip()] if code == 0 else []
    return {"code": int(code), "files": files, "err": err.strip()}


def _tracked_safety_gate(cwd: Path) -> dict[str, Any]:
    tracked = _git_tracked_files(cwd)
    if int(tracked["code"]) != 0:
        return {"code": int(tracked["code"]), "vault_tracked": [], "env_like_tracked": [], "err": tracked["err"]}
    files = [str(x) for x in tracked["files"] if isinstance(x, str)]
    vault_tracked = [x for x in files if x.startswith("vault/") or x.startswith("vault\\")]
    env_like_tracked = [
        x
        for x in files
        if Path(x).name.startswith(".env")
        and Path(x).name != ".env.example"
        and not Path(x).name.endswith(".example")
    ]
    code = 0 if not vault_tracked and not env_like_tracked else 1
    return {"code": code, "vault_tracked": vault_tracked, "env_like_tracked": env_like_tracked, "err": ""}


def _repo_visibility_gate(repo_slug: str, token: str | None) -> dict[str, Any]:
    slug = parse_repo_slug(str(repo_slug or "").strip())
    if not slug:
        return {"code": 1, "visibility": "", "repo": str(repo_slug or ""), "status": 0, "error_kind": "invalid_repo_slug", "err": "invalid repo slug"}
    owner, repo = slug
    res = github_api_request("GET", f"https://api.github.com/repos/{owner}/{repo}", token=token)
    visibility = str((res.json or {}).get("visibility", "")).strip().lower() if isinstance(res.json, dict) else ""
    if not res.ok:
        return {
            "code": 1,
            "visibility": visibility,
            "repo": f"{owner}/{repo}",
            "status": int(res.status),
            "error_kind": str(res.error_kind or ""),
            "err": str(res.error or ""),
        }
    code = 0 if visibility == "public" else 1
    return {
        "code": code,
        "visibility": visibility,
        "repo": f"{owner}/{repo}",
        "status": int(res.status),
        "error_kind": "",
        "err": "" if code == 0 else "repository is not public",
    }


def _desired_ruleset_policy() -> dict[str, Any]:
    return {
        "required_linear_history": True,
        "pull_request": {
            "required_approving_review_count": 2,
            "require_code_owner_review": True,
            "dismiss_stale_reviews_on_push": True,
            "required_review_thread_resolution": True,
        },
        "required_status_checks": {
            "strict_required_status_checks_policy": True,
            "required_checks": ["ci / test"],
        },
    }


def _extract_ruleset_policy(rules_list: list[Any]) -> dict[str, Any]:
    pull_request_rule = next(
        (r for r in rules_list if isinstance(r, dict) and str(r.get("type", "")) == "pull_request"),
        None,
    )
    pr_params = pull_request_rule.get("parameters", {}) if isinstance(pull_request_rule, dict) else {}
    status_checks_rule = next(
        (r for r in rules_list if isinstance(r, dict) and str(r.get("type", "")) == "required_status_checks"),
        None,
    )
    checks_params = status_checks_rule.get("parameters", {}) if isinstance(status_checks_rule, dict) else {}
    checks_raw = checks_params.get("required_checks", [])
    checks_list = checks_raw if isinstance(checks_raw, list) else []
    check_contexts = [str(x.get("context", "")) for x in checks_list if isinstance(x, dict)]
    return {
        "required_linear_history": any(
            isinstance(r, dict) and str(r.get("type", "")) == "required_linear_history" for r in rules_list
        ),
        "pull_request": {
            "required_approving_review_count": int(pr_params.get("required_approving_review_count", 0) or 0),
            "require_code_owner_review": bool(pr_params.get("require_code_owner_review", False)),
            "dismiss_stale_reviews_on_push": bool(pr_params.get("dismiss_stale_reviews_on_push", False)),
            "required_review_thread_resolution": bool(pr_params.get("required_review_thread_resolution", False)),
        },
        "required_status_checks": {
            "strict_required_status_checks_policy": bool(checks_params.get("strict_required_status_checks_policy", False)),
            "required_checks": check_contexts,
        },
    }


def _build_policy_diff(current: dict[str, Any], desired: dict[str, Any]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    if bool(current.get("required_linear_history", False)) != bool(desired.get("required_linear_history", False)):
        diffs.append(
            {
                "path": "rules.required_linear_history",
                "current": bool(current.get("required_linear_history", False)),
                "desired": bool(desired.get("required_linear_history", False)),
                "action": "set",
            }
        )
    current_pr = current.get("pull_request", {}) if isinstance(current.get("pull_request", {}), dict) else {}
    desired_pr = desired.get("pull_request", {}) if isinstance(desired.get("pull_request", {}), dict) else {}
    for key in (
        "required_approving_review_count",
        "require_code_owner_review",
        "dismiss_stale_reviews_on_push",
        "required_review_thread_resolution",
    ):
        if current_pr.get(key) != desired_pr.get(key):
            diffs.append(
                {
                    "path": f"rules.pull_request.{key}",
                    "current": current_pr.get(key),
                    "desired": desired_pr.get(key),
                    "action": "set",
                }
            )
    current_checks = (
        current.get("required_status_checks", {})
        if isinstance(current.get("required_status_checks", {}), dict)
        else {}
    )
    desired_checks = (
        desired.get("required_status_checks", {})
        if isinstance(desired.get("required_status_checks", {}), dict)
        else {}
    )
    if current_checks.get("strict_required_status_checks_policy") != desired_checks.get("strict_required_status_checks_policy"):
        diffs.append(
            {
                "path": "rules.required_status_checks.strict_required_status_checks_policy",
                "current": current_checks.get("strict_required_status_checks_policy"),
                "desired": desired_checks.get("strict_required_status_checks_policy"),
                "action": "set",
            }
        )
    current_contexts = [
        str(x)
        for x in (
            current_checks.get("required_checks", [])
            if isinstance(current_checks.get("required_checks", []), list)
            else []
        )
    ]
    desired_contexts = [
        str(x)
        for x in (
            desired_checks.get("required_checks", [])
            if isinstance(desired_checks.get("required_checks", []), list)
            else []
        )
    ]
    missing_contexts = [x for x in desired_contexts if x not in current_contexts]
    if missing_contexts:
        diffs.append(
            {
                "path": "rules.required_status_checks.required_checks",
                "current": current_contexts,
                "desired": desired_contexts,
                "action": "append_missing",
                "missing": missing_contexts,
            }
        )
    return diffs


def _repo_ruleset_gate(repo_slug: str, token: str | None, ruleset_name: str = "integrator-main-protection") -> dict[str, Any]:
    slug = parse_repo_slug(str(repo_slug or "").strip())
    if not slug:
        return {
            "code": 1,
            "repo": str(repo_slug or ""),
            "ruleset_name": str(ruleset_name),
            "status": 0,
            "error_kind": "invalid_repo_slug",
            "err": "invalid repo slug",
        }
    owner, repo = slug
    res = github_api_request("GET", f"https://api.github.com/repos/{owner}/{repo}/rulesets", token=token)
    if not res.ok:
        return {
            "code": 1,
            "repo": f"{owner}/{repo}",
            "ruleset_name": str(ruleset_name),
            "status": int(res.status),
            "error_kind": str(res.error_kind or ""),
            "err": str(res.error or ""),
        }
    payload: list[Any] = res.json if isinstance(res.json, list) else []
    matched: dict[str, Any] | None = None
    for item in payload:
        if not isinstance(item, dict):
            continue
        if str(item.get("name", "")) == str(ruleset_name):
            matched = item
            break
    if not isinstance(matched, dict):
        return {
            "code": 1,
            "repo": f"{owner}/{repo}",
            "ruleset_name": str(ruleset_name),
            "status": int(res.status),
            "error_kind": "ruleset_missing",
            "err": "ruleset not found",
        }
    enforcement = str(matched.get("enforcement", "")).strip().lower()
    ruleset_id = int(matched.get("id", 0) or 0)
    if enforcement != "active":
        return {
            "code": 1,
            "repo": f"{owner}/{repo}",
            "ruleset_name": str(ruleset_name),
            "ruleset_id": ruleset_id,
            "enforcement": enforcement,
            "status": int(res.status),
            "error_kind": "ruleset_not_active",
            "err": "ruleset is not active",
        }
    if ruleset_id <= 0:
        return {
            "code": 1,
            "repo": f"{owner}/{repo}",
            "ruleset_name": str(ruleset_name),
            "ruleset_id": 0,
            "enforcement": enforcement,
            "status": int(res.status),
            "error_kind": "ruleset_missing_id",
            "err": "ruleset id is missing",
        }
    details = github_api_request("GET", f"https://api.github.com/repos/{owner}/{repo}/rulesets/{ruleset_id}", token=token)
    if not details.ok:
        return {
            "code": 1,
            "repo": f"{owner}/{repo}",
            "ruleset_name": str(ruleset_name),
            "ruleset_id": ruleset_id,
            "enforcement": enforcement,
            "status": int(details.status),
            "error_kind": "ruleset_read_failed",
            "err": str(details.error or ""),
        }
    rules = details.json.get("rules") if isinstance(details.json, dict) else None
    rules_list: list[Any] = rules if isinstance(rules, list) else []
    current_policy = _extract_ruleset_policy(rules_list)
    desired_policy = _desired_ruleset_policy()
    policy_diff = _build_policy_diff(current_policy, desired_policy)
    code = 0 if not policy_diff else 1
    return {
        "code": code,
        "repo": f"{owner}/{repo}",
        "ruleset_name": str(ruleset_name),
        "ruleset_id": ruleset_id,
        "enforcement": enforcement,
        "status": int(details.status),
        "required_checks": current_policy["required_status_checks"]["required_checks"],
        "ruleset_details": details.json if isinstance(details.json, dict) else {},
        "policy_current": current_policy,
        "policy_desired": desired_policy,
        "policy_diff": policy_diff,
        "error_kind": "" if code == 0 else "ruleset_policy_mismatch",
        "err": "" if code == 0 else ", ".join(str(x.get("path", "")) for x in policy_diff),
    }


def _build_ruleset_remediation_plan(repo_slug: str, gate: dict[str, Any]) -> dict[str, Any]:
    ruleset_details = gate.get("ruleset_details", {}) if isinstance(gate.get("ruleset_details", {}), dict) else {}
    current_rules_raw = ruleset_details.get("rules", []) if isinstance(ruleset_details, dict) else []
    current_rules = [x for x in current_rules_raw if isinstance(x, dict)] if isinstance(current_rules_raw, list) else []
    base_rules = [x for x in current_rules if str(x.get("type", "")) != "required_status_checks"]
    pull_request_rule = next((x for x in base_rules if str(x.get("type", "")) == "pull_request"), None)
    pull_request_params = (
        pull_request_rule.get("parameters", {})
        if isinstance(pull_request_rule, dict) and isinstance(pull_request_rule.get("parameters", {}), dict)
        else {}
    )
    pull_request_with_nested = dict(pull_request_params)
    pull_request_with_nested["required_status_checks"] = [{"context": "ci / test"}]
    base_payload: dict[str, Any] = {
        "name": str(gate.get("ruleset_name", "integrator-main-protection")),
        "target": str(ruleset_details.get("target", "branch") if isinstance(ruleset_details, dict) else "branch"),
        "enforcement": str(gate.get("enforcement", "active")),
        "conditions": ruleset_details.get("conditions", {"ref_name": {"include": ["refs/heads/main"], "exclude": []}})
        if isinstance(ruleset_details, dict)
        else {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
    }
    candidate_payloads = [
        {
            "id": "candidate_rule_strict",
            "label": "required_status_checks rule with strict policy",
            "payload": {
                **base_payload,
                "rules": [
                    *base_rules,
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "strict_required_status_checks_policy": True,
                            "required_checks": [{"context": "ci / test"}],
                        },
                    },
                ],
            },
        },
        {
            "id": "candidate_rule_simple",
            "label": "required_status_checks rule with required checks only",
            "payload": {
                **base_payload,
                "rules": [
                    *base_rules,
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_checks": [{"context": "ci / test"}],
                        },
                    },
                ],
            },
        },
        {
            "id": "candidate_pull_request_nested",
            "label": "pull_request nested required_status_checks",
            "payload": {
                **base_payload,
                "rules": [
                    (
                        {
                            **pull_request_rule,
                            "parameters": pull_request_with_nested,
                        }
                        if isinstance(pull_request_rule, dict) and str(x.get("type", "")) == "pull_request"
                        else x
                    )
                    for x in base_rules
                ],
            },
        },
    ]
    return {
        "kind": "ruleset_remediation_plan",
        "mode": "plan_only",
        "repo": str(repo_slug),
        "ruleset_name": str(gate.get("ruleset_name", "")),
        "ruleset_id": int(gate.get("ruleset_id", 0) or 0),
        "safety": {
            "blind_put": False,
            "requires_manual_review": True,
            "requires_owner_confirmation": True,
        },
        "policy_current": gate.get("policy_current", {}),
        "policy_desired": gate.get("policy_desired", {}),
        "policy_diff": gate.get("policy_diff", []),
        "candidate_payloads": candidate_payloads,
        "proposed_actions": [
            "Сохранить текущий ruleset GET-слепок в отдельный артефакт.",
            "Запустить remote probe с shape-adapter и собрать compatible_payload.",
            "Применить compatible_payload вручную с --confirm APPLY.",
            "Проверить post-check readiness и зафиксировать итог.",
        ],
    }


def _sanitize_rule_params(rule_type: str, params: dict[str, Any]) -> dict[str, Any]:
    if rule_type == "pull_request":
        keys = {
            "required_approving_review_count",
            "dismiss_stale_reviews_on_push",
            "required_reviewers",
            "require_code_owner_review",
            "require_last_push_approval",
            "required_review_thread_resolution",
            "allowed_merge_methods",
            "required_status_checks",
        }
        return {k: params[k] for k in keys if k in params}
    if rule_type == "required_status_checks":
        keys = {"strict_required_status_checks_policy", "required_checks", "checks"}
        return {k: params[k] for k in keys if k in params}
    return dict(params)


def _sanitize_ruleset_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("name", "target", "enforcement", "conditions", "rules"):
        if key in payload:
            out[key] = payload[key]
    raw_rules = out.get("rules", []) if isinstance(out.get("rules", []), list) else []
    rules: list[dict[str, Any]] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            continue
        rtype = str(item.get("type", ""))
        if not rtype:
            continue
        rule: dict[str, Any] = {"type": rtype}
        params = item.get("parameters", {})
        if isinstance(params, dict):
            rule["parameters"] = _sanitize_rule_params(rtype, params)
        rules.append(rule)
    out["rules"] = rules
    return out


def _to_required_checks_as_strings(payload: dict[str, Any]) -> dict[str, Any]:
    out = _sanitize_ruleset_payload(payload)
    rules = out.get("rules", []) if isinstance(out.get("rules", []), list) else []
    converted: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rtype = str(rule.get("type", ""))
        params = rule.get("parameters", {})
        if rtype == "required_status_checks" and isinstance(params, dict):
            checks_raw = params.get("required_checks", [])
            checks = checks_raw if isinstance(checks_raw, list) else []
            contexts = [str(x.get("context", "")) for x in checks if isinstance(x, dict) and str(x.get("context", ""))]
            next_params = dict(params)
            next_params["required_checks"] = contexts
            converted.append({"type": rtype, "parameters": next_params})
        else:
            converted.append(rule)
    out["rules"] = converted
    return out


def _to_required_status_checks_alt_key(payload: dict[str, Any]) -> dict[str, Any]:
    out = _sanitize_ruleset_payload(payload)
    rules = out.get("rules", []) if isinstance(out.get("rules", []), list) else []
    converted: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rtype = str(rule.get("type", ""))
        params = rule.get("parameters", {})
        if rtype == "required_status_checks" and isinstance(params, dict):
            checks_raw = params.get("required_checks", [])
            checks = checks_raw if isinstance(checks_raw, list) else []
            contexts = [str(x.get("context", "")) for x in checks if isinstance(x, dict) and str(x.get("context", ""))]
            converted.append(
                {
                    "type": rtype,
                    "parameters": {
                        "strict_required_status_checks_policy": bool(
                            params.get("strict_required_status_checks_policy", False)
                        ),
                        "checks": contexts,
                    },
                }
            )
        else:
            converted.append(rule)
    out["rules"] = converted
    return out


def _to_minimal_pull_request(payload: dict[str, Any]) -> dict[str, Any]:
    out = _sanitize_ruleset_payload(payload)
    rules = out.get("rules", []) if isinstance(out.get("rules", []), list) else []
    converted: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rtype = str(rule.get("type", ""))
        params = rule.get("parameters", {})
        if rtype == "pull_request" and isinstance(params, dict):
            converted.append(
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": int(params.get("required_approving_review_count", 2) or 2),
                        "dismiss_stale_reviews_on_push": bool(params.get("dismiss_stale_reviews_on_push", True)),
                        "require_code_owner_review": bool(params.get("require_code_owner_review", True)),
                        "required_review_thread_resolution": bool(params.get("required_review_thread_resolution", True)),
                    },
                }
            )
        else:
            converted.append(rule)
    out["rules"] = converted
    return out


def _adapter_variants_for_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"adapter_id": "identity_pruned", "adapter_kind": "prune_unknown", "payload": _sanitize_ruleset_payload(payload)},
        {"adapter_id": "checks_as_strings", "adapter_kind": "alternative_keys", "payload": _to_required_checks_as_strings(payload)},
        {"adapter_id": "status_checks_alt_key", "adapter_kind": "alternative_keys", "payload": _to_required_status_checks_alt_key(payload)},
        {"adapter_id": "minimal_pull_request", "adapter_kind": "minimize_fields", "payload": _to_minimal_pull_request(payload)},
    ]


def _probe_ruleset_candidate_payloads(repo_slug: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in candidates:
        cid = str(item.get("id", ""))
        payload = item.get("payload", {}) if isinstance(item.get("payload", {}), dict) else {}
        rules_raw = payload.get("rules", []) if isinstance(payload, dict) else []
        rules = rules_raw if isinstance(rules_raw, list) else []
        errors: list[str] = []
        warnings: list[str] = []
        if not isinstance(payload.get("name", None), str) or not str(payload.get("name", "")).strip():
            errors.append("missing_name")
        if str(payload.get("target", "")) != "branch":
            errors.append("invalid_target")
        if str(payload.get("enforcement", "")) not in {"active", "evaluate", "disabled"}:
            errors.append("invalid_enforcement")
        if not isinstance(rules, list) or not rules:
            errors.append("rules_empty")
        has_pull_request = any(isinstance(r, dict) and str(r.get("type", "")) == "pull_request" for r in rules)
        has_linear_history = any(isinstance(r, dict) and str(r.get("type", "")) == "required_linear_history" for r in rules)
        if not has_pull_request:
            errors.append("missing_pull_request_rule")
        if not has_linear_history:
            errors.append("missing_required_linear_history")
        status_checks_rule = next(
            (r for r in rules if isinstance(r, dict) and str(r.get("type", "")) == "required_status_checks"),
            None,
        )
        if isinstance(status_checks_rule, dict):
            params = status_checks_rule.get("parameters", {}) if isinstance(status_checks_rule.get("parameters", {}), dict) else {}
            checks = params.get("required_checks", [])
            if not isinstance(checks, list) or not checks:
                errors.append("required_status_checks.required_checks_empty")
        pull_request_rule = next(
            (r for r in rules if isinstance(r, dict) and str(r.get("type", "")) == "pull_request"),
            None,
        )
        if isinstance(pull_request_rule, dict):
            pr_params = (
                pull_request_rule.get("parameters", {})
                if isinstance(pull_request_rule.get("parameters", {}), dict)
                else {}
            )
            if "required_status_checks" in pr_params:
                warnings.append("nested_required_status_checks_known_422_risk")
        score = len(errors) * 100 + len(warnings) * 10
        results.append(
            {
                "id": cid,
                "label": str(item.get("label", "")),
                "supported": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "score": score,
            }
        )
    ranked = sorted(results, key=lambda x: (int(x.get("score", 0)), str(x.get("id", ""))))
    supported_ranked = [x for x in ranked if bool(x.get("supported", False))]
    recommended_id = str(supported_ranked[0].get("id", "")) if supported_ranked else ""
    return {
        "kind": "ruleset_probe_result",
        "mode": "dry_run_local",
        "repo": str(repo_slug),
        "mutation": "none",
        "recommended_candidate_id": recommended_id,
        "results": ranked,
    }


def _probe_ruleset_candidate_payloads_remote(
    repo_slug: str, token: str | None, candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    slug = parse_repo_slug(str(repo_slug or "").strip())
    if not slug:
        return {
            "kind": "ruleset_probe_result",
            "mode": "remote_temp_ruleset",
            "repo": str(repo_slug),
            "mutation": "temporary_create_delete",
            "error_kind": "invalid_repo_slug",
            "err": "invalid repo slug",
            "recommended_candidate_id": "",
            "results": [],
        }
    if not token:
        return {
            "kind": "ruleset_probe_result",
            "mode": "remote_temp_ruleset",
            "repo": str(repo_slug),
            "mutation": "temporary_create_delete",
            "error_kind": "missing_token",
            "err": "missing github token",
            "recommended_candidate_id": "",
            "results": [],
        }
    owner, repo = slug
    base_url = f"https://api.github.com/repos/{owner}/{repo}/rulesets"
    ts = _timestamp_compact()
    results: list[dict[str, Any]] = []
    adapter_failures: list[dict[str, Any]] = []
    compatible_payload: dict[str, Any] = {}
    for idx, item in enumerate(candidates):
        cid = str(item.get("id", ""))
        label = str(item.get("label", ""))
        raw_payload = item.get("payload", {}) if isinstance(item.get("payload", {}), dict) else {}
        adapter_results: list[dict[str, Any]] = []
        variants = _adapter_variants_for_payload(raw_payload)
        for v_idx, variant in enumerate(variants):
            adapter_id = str(variant.get("adapter_id", ""))
            adapter_kind = str(variant.get("adapter_kind", ""))
            payload_obj = variant.get("payload", {}) if isinstance(variant.get("payload", {}), dict) else {}
            probe_payload = dict(payload_obj)
            probe_payload["name"] = f"integrator-probe-{cid}-{adapter_id}-{ts}-{idx}-{v_idx}"
            probe_payload["target"] = "branch"
            probe_payload["enforcement"] = "disabled"
            probe_payload["conditions"] = {
                "ref_name": {
                    "include": [f"refs/heads/__integrator_probe__{ts}_{idx}_{v_idx}"],
                    "exclude": [],
                }
            }
            create_res = github_api_request("POST", base_url, token=token, payload=probe_payload)
            created_ruleset_id = 0
            cleanup_ok = False
            cleanup_status = 0
            cleanup_error = ""
            if create_res.ok and isinstance(create_res.json, dict):
                created_ruleset_id = int(create_res.json.get("id", 0) or 0)
                if created_ruleset_id > 0:
                    delete_res = github_api_request(
                        "DELETE",
                        f"{base_url}/{created_ruleset_id}",
                        token=token,
                        payload=None,
                    )
                    cleanup_ok = bool(delete_res.ok)
                    cleanup_status = int(delete_res.status)
                    cleanup_error = str(delete_res.error or "")
            supported = bool(create_res.ok) and bool(cleanup_ok)
            score = 0 if supported else (10 if create_res.ok else 100)
            adapter_result = {
                "adapter_id": adapter_id,
                "adapter_kind": adapter_kind,
                "supported": supported,
                "probe_status": int(create_res.status),
                "probe_error_kind": str(create_res.error_kind or ""),
                "probe_error": str(create_res.error or ""),
                "created_ruleset_id": created_ruleset_id,
                "cleanup_ok": cleanup_ok,
                "cleanup_status": cleanup_status,
                "cleanup_error": cleanup_error,
                "score": score,
            }
            adapter_results.append(adapter_result)
            if not supported:
                adapter_failures.append(
                    {
                        "candidate_id": cid,
                        "adapter_id": adapter_id,
                        "adapter_kind": adapter_kind,
                        "probe_status": int(create_res.status),
                        "probe_error_kind": str(create_res.error_kind or ""),
                        "probe_error": str(create_res.error or ""),
                    }
                )
            if supported and not compatible_payload:
                compatible_payload = {
                    "candidate_id": cid,
                    "candidate_label": label,
                    "adapter_id": adapter_id,
                    "adapter_kind": adapter_kind,
                    "payload": payload_obj,
                }
        best_adapter = sorted(adapter_results, key=lambda x: (int(x.get("score", 0)), str(x.get("adapter_id", ""))))
        selected_adapter = best_adapter[0] if best_adapter else {}
        supported = bool(selected_adapter.get("supported", False))
        results.append(
            {
                "id": cid,
                "label": label,
                "supported": supported,
                "selected_adapter_id": str(selected_adapter.get("adapter_id", "")),
                "selected_adapter_kind": str(selected_adapter.get("adapter_kind", "")),
                "probe_status": int(selected_adapter.get("probe_status", 0) or 0),
                "probe_error_kind": str(selected_adapter.get("probe_error_kind", "")),
                "probe_error": str(selected_adapter.get("probe_error", "")),
                "cleanup_ok": bool(selected_adapter.get("cleanup_ok", False)),
                "cleanup_status": int(selected_adapter.get("cleanup_status", 0) or 0),
                "cleanup_error": str(selected_adapter.get("cleanup_error", "")),
                "score": int(selected_adapter.get("score", 1000) or 1000),
                "adapter_attempts": adapter_results,
            }
        )
    ranked = sorted(results, key=lambda x: (int(x.get("score", 0)), str(x.get("id", ""))))
    supported_ranked = [x for x in ranked if bool(x.get("supported", False))]
    recommended_id = str(supported_ranked[0].get("id", "")) if supported_ranked else ""
    return {
        "kind": "ruleset_probe_result",
        "mode": "remote_temp_ruleset",
        "repo": f"{owner}/{repo}",
        "mutation": "temporary_create_delete",
        "recommended_candidate_id": recommended_id,
        "compatible_payload": compatible_payload,
        "adapter_failures": [] if compatible_payload else adapter_failures,
        "results": ranked,
    }


def _collect_public_readiness_gates(repo_slug: str, token: str | None, python_cmd: str, cwd: Path) -> dict[str, Any]:
    return {
        "no_secrets": _no_secrets_gate(python_cmd, cwd),
        "tracked_safety": _tracked_safety_gate(cwd),
        "repo_visibility": _repo_visibility_gate(repo_slug, token),
        "repo_ruleset": _repo_ruleset_gate(repo_slug, token),
    }


def _api_shape_compatibility_gate(
    repo_slug: str,
    repo_ruleset_gate: dict[str, Any],
    remediation_payload: dict[str, Any] | None,
    probe_enabled: bool,
    probe_on_remote: bool,
) -> dict[str, Any]:
    if str(repo_ruleset_gate.get("error_kind", "")) != "ruleset_policy_mismatch":
        return {
            "code": 0,
            "repo": str(repo_slug),
            "mode": "not_required",
            "supported": True,
            "error_kind": "",
            "err": "",
        }
    if not probe_enabled:
        return {
            "code": 1,
            "repo": str(repo_slug),
            "mode": "probe_disabled",
            "supported": False,
            "error_kind": "probe_not_run",
            "err": "enable --probe-ruleset-payloads",
        }
    if not probe_on_remote:
        return {
            "code": 1,
            "repo": str(repo_slug),
            "mode": "local_only",
            "supported": False,
            "error_kind": "remote_probe_required",
            "err": "enable --probe-on-remote for API compatibility signal",
        }
    probe = remediation_payload.get("probe", {}) if isinstance(remediation_payload, dict) else {}
    compatible = probe.get("compatible_payload", {}) if isinstance(probe, dict) else {}
    supported = isinstance(compatible, dict) and bool(compatible)
    return {
        "code": 0 if supported else 1,
        "repo": str(repo_slug),
        "mode": "remote_temp_ruleset",
        "supported": supported,
        "recommended_candidate_id": str(probe.get("recommended_candidate_id", "")) if isinstance(probe, dict) else "",
        "error_kind": "" if supported else "shape_unsupported",
        "err": "" if supported else "no compatible payload found by remote probe",
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text_atomic(path, text, backup=True)


def _write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    issues = payload.get("issues", [])
    pulls = payload.get("pulls", [])
    lines: list[str] = [
        "# GitHub snapshot",
        "",
        f"- repo: `{payload.get('repo', '')}`",
        f"- state: `{payload.get('state', '')}`",
        f"- timestamp: `{payload.get('timestamp', '')}`",
        f"- issues_open_count: `{payload.get('issues_open_count', 0)}`",
        f"- pulls_open_count: `{payload.get('pulls_open_count', 0)}`",
        "",
        "## Open issues",
        "",
        "| number | title | updated_at | url |",
        "|---:|---|---|---|",
    ]
    for item in issues if isinstance(issues, list) else []:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {int(item.get('number', 0))} | {str(item.get('title', '')).replace('|', '/')} | {item.get('updated_at', '')} | {item.get('html_url', '')} |"
        )
    if not isinstance(issues, list) or not issues:
        lines.append("| 0 | - | - | - |")

    lines.extend(
        [
            "",
            "## Open pull requests",
            "",
            "| number | title | draft | updated_at | url |",
            "|---:|---|---:|---|---|",
        ]
    )
    for item in pulls if isinstance(pulls, list) else []:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {int(item.get('number', 0))} | {str(item.get('title', '')).replace('|', '/')} | {int(bool(item.get('draft', False)))} | {item.get('updated_at', '')} | {item.get('html_url', '')} |"
        )
    if not isinstance(pulls, list) or not pulls:
        lines.append("| 0 | - | 0 | - | - |")

    _write_text_atomic(path, "\n".join(lines) + "\n", backup=True)


def _timestamp_compact() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _github_list_all(url: str, token: str | None) -> dict[str, Any]:
    page = 1
    per_page = 100
    items: list[dict[str, Any]] = []
    while True:
        sep = "&" if "?" in url else "?"
        page_url = f"{url}{sep}{urlencode({'per_page': per_page, 'page': page})}"
        res = github_api_request("GET", page_url, token=token)
        if not res.ok:
            return {"ok": False, "status": int(res.status), "error": res.error or "", "items": items}
        payload: list[Any] = res.json if isinstance(res.json, list) else []
        chunk = [x for x in payload if isinstance(x, dict)]
        items.extend(chunk)
        if len(chunk) < per_page:
            break
        page += 1
    return {"ok": True, "status": 200, "error": "", "items": items}


def _cmd_quality_github_snapshot(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    slug = parse_repo_slug(str(args.repo or "").strip())
    if not slug:
        _print_tab(["error", "invalid_repo_slug", str(args.repo or "")])
        return 2
    owner, repo = slug
    token = load_github_token()
    state = str(args.state or "open").strip() or "open"
    base = f"https://api.github.com/repos/{owner}/{repo}"
    issues_url = f"{base}/issues?state={state}"
    pulls_url = f"{base}/pulls?state={state}"

    issues_res = _github_list_all(issues_url, token)
    pulls_res = _github_list_all(pulls_url, token)
    if not bool(issues_res.get("ok", False)) or not bool(pulls_res.get("ok", False)):
        payload = {
            "kind": "github_snapshot",
            "repo": f"{owner}/{repo}",
            "state": state,
            "token_present": bool(token),
            "issues": issues_res,
            "pulls": pulls_res,
        }
        if args.json:
            _print_json(payload)
        return 1

    issues_raw = [x for x in issues_res["items"] if "pull_request" not in x]
    pulls_raw = list(pulls_res["items"])
    issues = [
        {
            "number": int(x.get("number", 0)),
            "title": str(x.get("title", "")),
            "state": str(x.get("state", "")),
            "updated_at": str(x.get("updated_at", "")),
            "html_url": str(x.get("html_url", "")),
        }
        for x in issues_raw
    ]
    pulls = [
        {
            "number": int(x.get("number", 0)),
            "title": str(x.get("title", "")),
            "state": str(x.get("state", "")),
            "draft": bool(x.get("draft", False)),
            "updated_at": str(x.get("updated_at", "")),
            "html_url": str(x.get("html_url", "")),
        }
        for x in pulls_raw
    ]
    payload = {
        "kind": "github_snapshot",
        "timestamp": _timestamp_compact(),
        "repo": f"{owner}/{repo}",
        "state": state,
        "token_present": bool(token),
        "issues_open_count": len(issues),
        "pulls_open_count": len(pulls),
        "issues": issues,
        "pulls": pulls,
    }

    out_path = (
        Path(args.write_report).resolve()
        if args.write_report
        else (cwd / "reports" / f"github_snapshot_{_timestamp_compact()}.json").resolve()
    )
    md_path = out_path.with_suffix(".md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifacts"] = {"report_json": str(out_path), "report_md": str(md_path)}
    _write_report(out_path, payload)
    _write_markdown_report(md_path, payload)
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["repo", payload["repo"]])
        _print_tab(["state", payload["state"]])
        _print_tab(["issues_open_count", payload["issues_open_count"]])
        _print_tab(["pulls_open_count", payload["pulls_open_count"]])
        _print_tab(["report_json", str(out_path)])
        _print_tab(["report_md", str(md_path)])
    return 0


def _parse_iso_utc(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)
    except ValueError:
        return None


def _cmd_quality_projects_migration_readiness(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    slug = parse_repo_slug(str(getattr(args, "repo", "") or "").strip())
    if not slug:
        _print_tab(["error", "invalid_repo_slug", str(getattr(args, "repo", "") or "")])
        return 2
    owner, repo = slug
    token = load_github_token()
    base = f"https://api.github.com/repos/{owner}/{repo}"
    issues_res = _github_list_all(f"{base}/issues?state=open", token)
    pulls_res = _github_list_all(f"{base}/pulls?state=open", token)
    if not bool(issues_res.get("ok", False)) or not bool(pulls_res.get("ok", False)):
        payload: dict[str, Any] = {
            "kind": "projects_migration_readiness",
            "repo": f"{owner}/{repo}",
            "ok": False,
            "error_kind": "github_api_unavailable",
            "issues": issues_res,
            "pulls": pulls_res,
        }
        if args.json:
            _print_json(payload)
        return 1

    issues_all = [x for x in issues_res.get("items", []) if isinstance(x, dict)]
    open_issues = [x for x in issues_all if "pull_request" not in x]
    open_pulls = [x for x in pulls_res.get("items", []) if isinstance(x, dict)]
    stale_days = int(getattr(args, "stale_days", 7))
    now_utc = datetime.now(timezone.utc)
    stale_issues = 0
    unlabeled_issues = 0
    triaged_issues = 0
    for item in open_issues:
        updated_at = _parse_iso_utc(str(item.get("updated_at", "")))
        if updated_at is not None:
            age_days = (now_utc - updated_at).days
            if age_days >= stale_days:
                stale_issues += 1
        labels = item.get("labels", [])
        labels_list = [x for x in labels if isinstance(x, dict)] if isinstance(labels, list) else []
        label_names = [str(x.get("name", "")) for x in labels_list]
        if not label_names:
            unlabeled_issues += 1
        has_triage = any(
            name.startswith("priority:") or name.startswith("type:") or name.startswith("status:")
            for name in label_names
        )
        if has_triage:
            triaged_issues += 1

    score = 0
    reasons: list[str] = []
    issues_count = len(open_issues)
    pulls_count = len(open_pulls)
    triage_coverage = (triaged_issues / issues_count) if issues_count else 1.0
    if issues_count >= int(getattr(args, "issues_threshold", 6)):
        score += 1
        reasons.append("open_issues_above_threshold")
    if pulls_count >= int(getattr(args, "pulls_threshold", 3)):
        score += 1
        reasons.append("open_pulls_above_threshold")
    if stale_issues >= int(getattr(args, "stale_threshold", 3)):
        score += 1
        reasons.append("stale_issues_above_threshold")
    if triage_coverage < float(getattr(args, "triage_coverage_threshold", 0.6)):
        score += 1
        reasons.append("low_triage_coverage")
    recommend_projects = score >= int(getattr(args, "recommendation_score_threshold", 2))
    payload = {
        "kind": "projects_migration_readiness",
        "repo": f"{owner}/{repo}",
        "ok": True,
        "recommend_projects_migration": recommend_projects,
        "score": score,
        "score_threshold": int(getattr(args, "recommendation_score_threshold", 2)),
        "metrics": {
            "open_issues": issues_count,
            "open_pulls": pulls_count,
            "stale_issues": stale_issues,
            "unlabeled_issues": unlabeled_issues,
            "triaged_issues": triaged_issues,
            "triage_coverage": round(triage_coverage, 3),
            "stale_days": stale_days,
        },
        "thresholds": {
            "issues_threshold": int(getattr(args, "issues_threshold", 6)),
            "pulls_threshold": int(getattr(args, "pulls_threshold", 3)),
            "stale_threshold": int(getattr(args, "stale_threshold", 3)),
            "triage_coverage_threshold": float(getattr(args, "triage_coverage_threshold", 0.6)),
        },
        "reasons": reasons,
        "next_actions": (
            [
                "Создать GitHub Projects board: Backlog / Ready / In Progress / Review / Done.",
                "Добавить automation по label->status и SLA для stale issues.",
                "Перенести open issues в board с triage-лейблами.",
            ]
            if recommend_projects
            else [
                "Продолжить issue-only режим и повторить оценку через 7 дней.",
                "Повысить triage coverage и снизить stale issues.",
            ]
        ),
    }
    out_path = (
        Path(args.write_report).resolve()
        if getattr(args, "write_report", None)
        else (cwd / "reports" / f"projects_migration_readiness_{_timestamp_compact()}.json").resolve()
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifacts"] = {"report_json": str(out_path)}
    _write_report(out_path, payload)
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["repo", payload["repo"]])
        _print_tab(["recommend_projects_migration", payload["recommend_projects_migration"]])
        _print_tab(["score", payload["score"], payload["score_threshold"]])
        _print_tab(["open_issues", payload["metrics"]["open_issues"]])
        _print_tab(["open_pulls", payload["metrics"]["open_pulls"]])
        _print_tab(["stale_issues", payload["metrics"]["stale_issues"]])
        _print_tab(["triage_coverage", payload["metrics"]["triage_coverage"]])
        _print_tab(["report_json", str(out_path)])
    return 0


def _cmd_quality_mcp_tools_inventory(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    registry_path = (cwd / "registry.json").resolve()
    candidates: list[tuple[str, Path]] = []
    if registry_path.exists():
        try:
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            items = payload if isinstance(payload, list) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip() or "unknown"
                root_raw = str(item.get("root", "")).strip()
                if not root_raw:
                    continue
                root_path = Path(root_raw)
                if not root_path.is_absolute():
                    root_path = (cwd / root_path).resolve()
                candidates.append((name, root_path))
        except (OSError, json.JSONDecodeError):
            pass
    extra_roots = [str(x).strip() for x in (getattr(args, "roots", []) or []) if str(x).strip()]
    for root in extra_roots:
        candidates.append((f"extra:{Path(root).name or 'root'}", Path(root)))

    seen: set[str] = set()
    found: list[dict[str, Any]] = []
    for name, root in candidates:
        mcp_file = (root / "mcp_server.py").resolve()
        key = str(mcp_file).lower()
        if key in seen:
            continue
        seen.add(key)
        if mcp_file.exists():
            found.append(
                {
                    "name": name,
                    "root": str(root),
                    "mcp_server": str(mcp_file),
                    "start_command": f'python -m integrator localai assistant mcp --cwd "{root}" --daemon',
                }
            )
    payload: dict[str, Any] = {
        "kind": "mcp_tools_inventory",
        "cwd": str(cwd),
        "registry_path": str(registry_path),
        "mcp_servers_found": len(found),
        "servers": found,
    }
    out_path = (
        Path(args.write_report).resolve()
        if getattr(args, "write_report", None)
        else (cwd / "reports" / f"mcp_tools_inventory_{_timestamp_compact()}.json").resolve()
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifacts"] = {"report_json": str(out_path)}
    _write_report(out_path, payload)
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["mcp_servers_found", payload["mcp_servers_found"]])
        for item in found:
            _print_tab([item.get("name", ""), item.get("mcp_server", "")])
        _print_tab(["report_json", str(out_path)])
    return 0


def _cmd_quality_summary(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    python_cmd = sys.executable

    tools = {
        "python": {"executable": python_cmd, "version": sys.version.split()[0], "version_full": sys.version},
        "git": _tool_version(["git", "--version"], cwd),
        "ruff": _tool_version([python_cmd, "-m", "ruff", "--version"], cwd),
        "mypy": _tool_version([python_cmd, "-m", "mypy", "--version"], cwd),
        "coverage": _tool_version([python_cmd, "-m", "coverage", "--version"], cwd),
    }

    gates: dict[str, Any] = {}
    if not args.no_run:
        gates["no_secrets"] = _no_secrets_gate(python_cmd, cwd)
        gates["ruff"] = _gate([python_cmd, "-m", "ruff", "check", "."], cwd)
        gates["mypy"] = _gate([python_cmd, "-m", "mypy", "."], cwd)
        gates["unittest"] = _gate([python_cmd, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"], cwd)
        gates["coverage"] = _coverage_gate(python_cmd, cwd, int(args.fail_under))

    artifacts = {
        "coverage_xml": str((cwd / "reports" / "coverage.xml").resolve()),
        "security_gitleaks_json": str((cwd / "reports" / "gitleaks.json").resolve()),
        "security_gitleaks_sarif": str((cwd / "results.sarif").resolve()),
        "security_pip_audit_requirements_json": str((cwd / "reports" / "pip-audit-requirements.json").resolve()),
        "security_pip_audit_operator_json": str((cwd / "reports" / "pip-audit-operator.json").resolve()),
    }

    payload: dict[str, Any] = {
        "kind": "quality_summary",
        "cwd": str(cwd),
        "tools": tools,
        "gates": gates,
        "artifacts": artifacts,
    }

    out_path = Path(args.write_report).resolve() if args.write_report else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_report(out_path, payload)

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["cwd", payload["cwd"]])
        _print_tab(["python", tools["python"]["executable"], tools["python"]["version"]])
        for name in ("git", "ruff", "mypy", "coverage"):
            tv = tools[name]
            _print_tab([name, tv["code"], tv["out"] or tv["err"]])
        if gates:
            for name in ("no_secrets", "ruff", "mypy", "unittest", "coverage"):
                gv = gates.get(name, {})
                _print_tab([f"gate:{name}", gv.get("code", ""), (gv.get("out") or gv.get("err") or "")])
        _print_tab(["coverage.xml", artifacts["coverage_xml"]])
    any_failed = any(int(v.get("code", 0)) != 0 for v in gates.values()) if gates else False
    return 1 if any_failed else 0


def _cmd_quality_public_readiness(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    python_cmd = sys.executable
    repo_slug = str(getattr(args, "repo", "") or os.environ.get("GITHUB_REPOSITORY") or "").strip()
    token = load_github_token()
    gates = _collect_public_readiness_gates(repo_slug, token, python_cmd, cwd)
    remediation_enabled = bool(getattr(args, "auto_remediation_plan", False))
    probe_enabled = bool(getattr(args, "probe_ruleset_payloads", False))
    probe_on_remote = bool(getattr(args, "probe_on_remote", False))
    remediation_plan_path = ""
    remediation_payload: dict[str, Any] | None = None
    repo_ruleset_gate = gates.get("repo_ruleset", {})
    if remediation_enabled and isinstance(repo_ruleset_gate, dict):
        if str(repo_ruleset_gate.get("error_kind", "")) == "ruleset_policy_mismatch":
            remediation_payload = _build_ruleset_remediation_plan(repo_slug, repo_ruleset_gate)
            if probe_enabled:
                candidates_raw = remediation_payload.get("candidate_payloads", [])
                candidates = [x for x in candidates_raw if isinstance(x, dict)] if isinstance(candidates_raw, list) else []
                if probe_on_remote:
                    remediation_payload["probe"] = _probe_ruleset_candidate_payloads_remote(repo_slug, token, candidates)
                else:
                    remediation_payload["probe"] = _probe_ruleset_candidate_payloads(repo_slug, candidates)
                probe_payload = remediation_payload.get("probe", {})
                if isinstance(probe_payload, dict):
                    compatible = probe_payload.get("compatible_payload", {})
                    failures = probe_payload.get("adapter_failures", [])
                    remediation_payload["compatible_payload"] = compatible if isinstance(compatible, dict) else {}
                    remediation_payload["adapter_failures"] = failures if isinstance(failures, list) else []
            write_remediation_plan = str(getattr(args, "write_remediation_plan", "") or "").strip()
            remediation_out = (
                Path(write_remediation_plan).resolve()
                if write_remediation_plan
                else (cwd / "reports" / f"ruleset_remediation_plan_{_timestamp_compact()}.json").resolve()
            )
            remediation_out.parent.mkdir(parents=True, exist_ok=True)
            _write_report(remediation_out, remediation_payload)
            remediation_plan_path = str(remediation_out)
    api_shape_gate = _api_shape_compatibility_gate(
        repo_slug,
        repo_ruleset_gate if isinstance(repo_ruleset_gate, dict) else {},
        remediation_payload,
        probe_enabled,
        probe_on_remote,
    )
    gates["api_shape_compatibility"] = api_shape_gate
    any_failed = any(int(v.get("code", 0)) != 0 for v in gates.values())
    payload: dict[str, Any] = {
        "kind": "public_repo_readiness",
        "cwd": str(cwd),
        "ok": not any_failed,
        "gates": gates,
        "remediation": {
            "enabled": remediation_enabled,
            "generated": bool(remediation_plan_path),
            "probe_enabled": probe_enabled,
            "probe_on_remote": probe_on_remote,
            "probe_generated": bool(
                isinstance(remediation_payload, dict) and isinstance(remediation_payload.get("probe", None), dict)
            ),
        },
        "next_actions": {
            "branch_protection": {
                "required_checks": ["ci / test"],
                "required_approvals": 2,
                "dismiss_stale_approvals": True,
            }
        },
    }
    out_path = (
        Path(args.write_report).resolve()
        if args.write_report
        else (cwd / "reports" / f"public_repo_readiness_{_timestamp_compact()}.json").resolve()
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifacts"] = {"report_json": str(out_path), "remediation_plan_json": remediation_plan_path}
    _write_report(out_path, payload)
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["ok", payload["ok"]])
        for name in ("no_secrets", "tracked_safety", "repo_visibility", "repo_ruleset", "api_shape_compatibility"):
            gv = gates.get(name, {})
            _print_tab([f"gate:{name}", gv.get("code", ""), (gv.get("err") or "")])
        if remediation_plan_path:
            _print_tab(["remediation_plan_json", remediation_plan_path])
        _print_tab(["report_json", str(out_path)])
    return 1 if any_failed else 0


def _cmd_quality_apply_approved_candidate(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    python_cmd = sys.executable
    token = load_github_token()
    repo_slug = str(getattr(args, "repo", "") or os.environ.get("GITHUB_REPOSITORY") or "").strip()
    if str(getattr(args, "confirm", "")).strip() != "APPLY":
        _print_tab(["error", "confirm_required", "set --confirm APPLY"])
        return 2
    if not token:
        _print_tab(["error", "missing_token", "set GITHUB_TOKEN"])
        return 2
    slug = parse_repo_slug(repo_slug)
    if not slug:
        _print_tab(["error", "invalid_repo_slug", repo_slug])
        return 2
    plan_path = Path(str(getattr(args, "plan", ""))).resolve()
    if not plan_path.exists():
        _print_tab(["error", "plan_not_found", str(plan_path)])
        return 2
    plan_text = plan_path.read_text(encoding="utf-8")
    plan_payload = json.loads(plan_text)
    if not isinstance(plan_payload, dict) or str(plan_payload.get("kind", "")) != "ruleset_remediation_plan":
        _print_tab(["error", "invalid_plan_kind", str(plan_payload.get("kind", "")) if isinstance(plan_payload, dict) else ""])
        return 2
    use_compatible_payload = bool(getattr(args, "use_compatible_payload", False))
    candidate_id = str(getattr(args, "candidate_id", "")).strip()
    selected_payload: dict[str, Any] = {}
    selected_candidate_id = candidate_id
    if use_compatible_payload:
        compatible = plan_payload.get("compatible_payload", {}) if isinstance(plan_payload.get("compatible_payload", {}), dict) else {}
        if not isinstance(compatible, dict) or not compatible:
            _print_tab(["error", "compatible_payload_missing", "run remote probe with adapters first"])
            return 2
        comp_candidate_id = str(compatible.get("candidate_id", "")).strip()
        comp_payload = compatible.get("payload", {}) if isinstance(compatible.get("payload", {}), dict) else {}
        if not comp_candidate_id or not isinstance(comp_payload, dict) or not comp_payload:
            _print_tab(["error", "compatible_payload_invalid", "missing candidate_id or payload"])
            return 2
        if candidate_id and comp_candidate_id != candidate_id:
            _print_tab(["error", "candidate_mismatch_with_compatible_payload", f"{candidate_id} != {comp_candidate_id}"])
            return 2
        selected_candidate_id = comp_candidate_id
        selected_payload = comp_payload
    else:
        candidates_raw = (
            plan_payload.get("candidate_payloads", [])
            if isinstance(plan_payload.get("candidate_payloads", []), list)
            else []
        )
        candidates = [x for x in candidates_raw if isinstance(x, dict)]
        selected = next((x for x in candidates if str(x.get("id", "")) == candidate_id), None)
        if not isinstance(selected, dict):
            _print_tab(["error", "candidate_not_found", candidate_id])
            return 2
        selected_payload = selected.get("payload", {}) if isinstance(selected.get("payload", {}), dict) else {}
    ruleset_id = int(plan_payload.get("ruleset_id", 0) or 0)
    if ruleset_id <= 0:
        _print_tab(["error", "invalid_ruleset_id", str(ruleset_id)])
        return 2
    owner, repo = slug
    apply_res = github_api_request(
        "PUT",
        f"https://api.github.com/repos/{owner}/{repo}/rulesets/{ruleset_id}",
        token=token,
        payload=selected_payload,
    )
    post_gates = _collect_public_readiness_gates(repo_slug, token, python_cmd, cwd)
    post_ok = not any(int(v.get("code", 0)) != 0 for v in post_gates.values())
    post_report_path = (cwd / "reports" / f"public_repo_readiness_post_apply_{_timestamp_compact()}.json").resolve()
    post_report_path.parent.mkdir(parents=True, exist_ok=True)
    post_payload = {
        "kind": "public_repo_readiness",
        "cwd": str(cwd),
        "ok": post_ok,
        "gates": post_gates,
        "artifacts": {"report_json": str(post_report_path)},
    }
    _write_report(post_report_path, post_payload)
    out_path = (
        Path(args.write_report).resolve()
        if getattr(args, "write_report", None)
        else (cwd / "reports" / f"apply_approved_candidate_{_timestamp_compact()}.json").resolve()
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "apply_approved_candidate",
        "repo": f"{owner}/{repo}",
        "confirm": "APPLY",
        "plan_path": str(plan_path),
        "candidate_id": selected_candidate_id,
        "use_compatible_payload": use_compatible_payload,
        "ruleset_id": ruleset_id,
        "apply_result": dict(apply_res.__dict__),
        "post_check_ok": post_ok,
        "artifacts": {"report_json": str(out_path), "post_readiness_report_json": str(post_report_path)},
    }
    _write_report(out_path, payload)
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["apply_ok", bool(apply_res.ok)])
        _print_tab(["post_check_ok", post_ok])
        _print_tab(["report_json", str(out_path)])
        _print_tab(["post_readiness_report_json", str(post_report_path)])
    return 0 if bool(apply_res.ok) and post_ok else 1


def add_quality_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    quality = sub.add_parser("quality")
    quality_sub = quality.add_subparsers(dest="quality_cmd", required=True)

    summary = quality_sub.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    summary.add_argument("--no-run", action="store_true")
    summary.add_argument("--fail-under", type=int, default=80)
    summary.add_argument("--write-report", default=None)
    summary.set_defaults(func=_cmd_quality_summary)

    snapshot = quality_sub.add_parser("github-snapshot")
    snapshot.add_argument("--repo", required=True)
    snapshot.add_argument("--state", default="open")
    snapshot.add_argument("--write-report", default=None)
    snapshot.add_argument("--json", action="store_true")
    snapshot.set_defaults(func=_cmd_quality_github_snapshot)

    public_readiness = quality_sub.add_parser("public-readiness")
    public_readiness.add_argument("--repo", default=None)
    public_readiness.add_argument("--write-report", default=None)
    public_readiness.add_argument("--auto-remediation-plan", action="store_true")
    public_readiness.add_argument("--probe-ruleset-payloads", action="store_true")
    public_readiness.add_argument("--probe-on-remote", action="store_true")
    public_readiness.add_argument("--write-remediation-plan", default=None)
    public_readiness.add_argument("--json", action="store_true")
    public_readiness.set_defaults(func=_cmd_quality_public_readiness)

    apply_candidate = quality_sub.add_parser("apply-approved-candidate")
    apply_candidate.add_argument("--repo", default=None)
    apply_candidate.add_argument("--plan", required=True)
    apply_candidate.add_argument("--candidate-id", required=True)
    apply_candidate.add_argument("--use-compatible-payload", action="store_true")
    apply_candidate.add_argument("--confirm", required=True)
    apply_candidate.add_argument("--write-report", default=None)
    apply_candidate.add_argument("--json", action="store_true")
    apply_candidate.set_defaults(func=_cmd_quality_apply_approved_candidate)

    projects_ready = quality_sub.add_parser("projects-migration-readiness")
    projects_ready.add_argument("--repo", required=True)
    projects_ready.add_argument("--issues-threshold", type=int, default=6)
    projects_ready.add_argument("--pulls-threshold", type=int, default=3)
    projects_ready.add_argument("--stale-threshold", type=int, default=3)
    projects_ready.add_argument("--stale-days", type=int, default=7)
    projects_ready.add_argument("--triage-coverage-threshold", type=float, default=0.6)
    projects_ready.add_argument("--recommendation-score-threshold", type=int, default=2)
    projects_ready.add_argument("--write-report", default=None)
    projects_ready.add_argument("--json", action="store_true")
    projects_ready.set_defaults(func=_cmd_quality_projects_migration_readiness)

    mcp_inventory = quality_sub.add_parser("mcp-tools-inventory")
    mcp_inventory.add_argument("--roots", nargs="*", default=[])
    mcp_inventory.add_argument("--write-report", default=None)
    mcp_inventory.add_argument("--json", action="store_true")
    mcp_inventory.set_defaults(func=_cmd_quality_mcp_tools_inventory)
