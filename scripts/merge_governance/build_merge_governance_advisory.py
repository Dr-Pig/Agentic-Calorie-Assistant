from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / ".merge-governance.yml"
DEFAULT_JSON_OUT = ROOT / "artifacts" / "merge_governance_advisory.json"
DEFAULT_MD_OUT = ROOT / "artifacts" / "merge_governance_advisory.md"

DEFAULT_CONFIG: dict[str, Any] = {
    "main_branch": "main",
    "mainline_merge_policy": "mvp_and_governance_only",
    "mvp_mainline_tracks": ["AccurateIntake", "BodyBudgetCalibration", "CurrentShell", "FoodDB"],
    "future_shadow_tracks": ["LongTermContextLab", "RecommendationShadow", "RescueShadow", "ProactiveShadow"],
    "required_checks": [
        "repo-hygiene-and-architecture",
        "runtime-contract-tests",
        "product-pages-browser-e2e",
    ],
    "advisory_checks": [],
    "forbidden_future_runtime_effects": [
        {"runtime_truth_changed": True},
        {"manager_context_packet_changed": True},
        {"mutation_changed": True},
        {"product_readiness_claimed": True},
        {"durable_memory_written": True},
        {"proactive_sent": True},
        {"recommendation_served": True},
        {"rescue_committed": True},
        {"day_budget_mutated": True},
        {"body_plan_mutated": True},
        {"meal_thread_mutated": True},
    ],
    "size_budget": {
        "mvp_mainline_max_additions": 600,
        "future_shadow_merge_max_additions": 250,
        "dormant_shadow_max_additions": 15000,
        "max_stack_depth": 2,
        "max_branch_age_days_without_realign": 2,
    },
}

REQUIRED_TRACK_REPORT_KEYS = (
    "track",
    "runtime_truth_changed",
    "manager_context_packet_changed",
    "mutation_changed",
    "product_readiness_claimed",
)
READY_FOR_QUEUE_MARKER = "READY_FOR_QUEUE"
CURRENT_SHELL_SYNC_CONTRACT_PATH = ROOT / "docs" / "quality" / "CURRENT_SHELL_SYNC_CONTRACT.yaml"
CURRENT_SHELL_OWNER_LANES = {"ManagerRuntime", "AppShell", "SharedCurrentShell"}
CURRENT_SHELL_LAUNCH_CLAIM_SCOPES = {"none"}

SUCCESS_CONCLUSIONS = {"SUCCESS", "SKIPPED", "NEUTRAL"}
FAIL_CONCLUSIONS = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
TRANSIENT_GH_ERROR_TOKENS = (
    "HTTP 502",
    "HTTP 503",
    "HTTP 504",
    "connection reset",
    "timeout",
    "timed out",
)

STALE_CONTRACT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("legacy_calibration_unmounted_route_gate", r"calibration_action_router_stays_unmounted_until_activation_plan"),
    ("legacy_calibration_unmounted_route_gate", r"assert\s+[\"']calibration_router[\"']\s+not\s+in\s+source"),
)

CONTRACT_DRIFT_SCAN_EXCLUDES = (
    ".merge-governance.yml",
    ".github/workflows/merge-governance.yml",
    "scripts/merge_governance/",
    "tests/test_merge_governance_",
)

FUTURE_ACTIVE_SURFACE_PATTERNS = (
    "app/routes.py",
    "app/main.py",
    "app/runtime/agent/",
    "app/runtime/interface/",
    "app/composition/",
    "alembic/",
    "migrations/",
)

PROACTIVE_SHADOW_ALLOWED_RUNTIME_APPLICATION_PATHS = {
    "app/runtime/application/proactive_no_send_shadow_evaluator.py",
}

GUARD_OR_CONTRACT_TOKENS = (
    "guard",
    "contract",
    "matrix",
    "readiness",
    "activation",
    "artifact_gate",
    "boundary",
    "governance",
)


def _parse_scalar(value: str) -> Any:
    normalized = value.strip()
    if normalized.lower() == "true":
        return True
    if normalized.lower() == "false":
        return False
    if normalized.lower() in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", normalized):
        return int(normalized)
    return normalized.strip('"').strip("'")


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            key, _, value = line.partition(":")
            current_key = key.strip()
            if value.strip():
                data[current_key] = _parse_scalar(value)
            elif current_key == "size_budget":
                data[current_key] = {}
            else:
                data[current_key] = []
            continue
        if current_key is None:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if ":" in item:
                key, _, value = item.partition(":")
                data.setdefault(current_key, []).append({key.strip(): _parse_scalar(value)})
            else:
                data.setdefault(current_key, []).append(_parse_scalar(item))
            continue
        if ":" in stripped and isinstance(data.get(current_key), dict):
            key, _, value = stripped.partition(":")
            data[current_key][key.strip()] = _parse_scalar(value)
    return data


def _merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)
    parsed = _parse_yaml_subset(path.read_text(encoding="utf-8"))
    return _merge_config(DEFAULT_CONFIG, parsed)


def _is_transient_gh_error(command: list[str], stderr: str) -> bool:
    if not command or command[0] != "gh":
        return False
    lowered = stderr.lower()
    return any(token.lower() in lowered for token in TRANSIENT_GH_ERROR_TOKENS)


def _run_json(command: list[str], *, retries: int = 3, retry_delay_seconds: float = 1.0) -> Any:
    attempts = max(retries, 1)
    last_error = ""
    for attempt in range(1, attempts + 1):
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode == 0:
            return json.loads(completed.stdout)
        last_error = completed.stderr.strip()
        if attempt >= attempts or not _is_transient_gh_error(command, last_error):
            break
        time.sleep(retry_delay_seconds * attempt)
    raise RuntimeError(f"{' '.join(command)} failed: {last_error}")


def _run_text(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _ref_exists(ref: str) -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _head_contains_main(*, head: str, main_branch: str) -> bool | None:
    main_ref = f"origin/{main_branch}"
    head_ref = f"origin/{head}"
    if not _ref_exists(main_ref) or not _ref_exists(head_ref):
        return None
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", main_ref, head_ref],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _github_repository() -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repository:
        return repository
    data = _run_json(["gh", "repo", "view", "--json", "nameWithOwner"])
    value = str(data.get("nameWithOwner") or "").strip()
    if not value:
        raise RuntimeError("Unable to resolve GitHub repository nameWithOwner.")
    return value


def _fetch_pr_files(*, pr_number: int, repository: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page = 1
    while True:
        endpoint = f"repos/{repository}/pulls/{pr_number}/files?per_page=100&page={page}"
        batch = _run_json(["gh", "api", endpoint])
        if not isinstance(batch, list):
            raise RuntimeError(f"Expected list of pull request files for PR {pr_number}, got: {type(batch).__name__}")
        for item in batch:
            files.append(
                {
                    "path": _normalize_repo_path(str(item.get("filename") or "")),
                    "additions": int(item.get("additions") or 0),
                    "deletions": int(item.get("deletions") or 0),
                }
            )
        if len(batch) < 100:
            break
        page += 1
    return files


def collect_open_prs(*, config: dict[str, Any], include_diffs: bool = True, limit: int = 80) -> list[dict[str, Any]]:
    fields = ",".join(
        [
            "number",
            "title",
            "headRefName",
            "headRefOid",
            "baseRefName",
            "baseRefOid",
            "body",
            "isDraft",
            "mergeStateStatus",
            "statusCheckRollup",
            "updatedAt",
            "url",
            "additions",
            "deletions",
            "changedFiles",
        ]
    )
    prs = _run_json(["gh", "pr", "list", "--state", "open", "--limit", str(limit), "--json", fields])
    repository = _github_repository()
    for pr in prs:
        pr_number = int(pr.get("number") or 0)
        pr["files"] = _fetch_pr_files(pr_number=pr_number, repository=repository) if pr_number else []
        pr["head_contains_main"] = _head_contains_main(
            head=str(pr.get("headRefName") or ""),
            main_branch=str(config.get("main_branch") or "main"),
        )
        pr["contract_findings"] = _contract_findings_from_ref(str(pr.get("headRefName") or ""))
        if include_diffs:
            pr["diff_text"] = _run_text(["gh", "pr", "diff", str(pr.get("number")), "--patch"])
    return prs


def _contract_findings_from_ref(head: str) -> list[str]:
    ref = f"origin/{head}"
    if not head or not _ref_exists(ref):
        return []
    findings: list[str] = []
    for code, pattern in STALE_CONTRACT_PATTERNS:
        completed = subprocess.run(
            ["git", "grep", "-n", "-E", pattern, ref, "--", "tests", "app", "docs", "scripts"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            continue
        relevant_lines = [
            line
            for line in completed.stdout.splitlines()
            if not any(excluded in line for excluded in CONTRACT_DRIFT_SCAN_EXCLUDES)
        ]
        if relevant_lines:
            findings.append(code)
    return sorted(set(findings))


def extract_track_report(body: str) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for line in body.splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.+?)\s*$", line)
        if not match:
            continue
        key, value = match.groups()
        report[key] = _parse_scalar(value)
    return report


def has_ready_for_queue(body: str) -> bool:
    return READY_FOR_QUEUE_MARKER in body


def _csv_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        text = str(value).strip()
        if not text:
            return []
        items = text.split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def load_current_shell_sync_contract(path: Path = CURRENT_SHELL_SYNC_CONTRACT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _parse_yaml_subset(path.read_text(encoding="utf-8"))


def current_shell_metadata(flags: dict[str, Any]) -> dict[str, Any]:
    shell_surface_impacted = flags.get("shell_surface_impacted")
    launch_claim_scope_raw = flags.get("launch_claim_scope")
    if not isinstance(shell_surface_impacted, bool):
        normalized = str(shell_surface_impacted or "").strip().lower()
        if normalized == "true":
            shell_surface_impacted = True
        elif normalized == "false":
            shell_surface_impacted = False
        elif normalized == "":
            shell_surface_impacted = None
    if launch_claim_scope_raw is None and "launch_claim_scope" in flags:
        launch_claim_scope = "none"
    else:
        launch_claim_scope = str(launch_claim_scope_raw or "").strip()
    return {
        "owner_lane": str(flags.get("owner_lane") or "").strip(),
        "slice_class": str(flags.get("slice_class") or "").strip(),
        "pass_type": str(flags.get("pass_type") or "").strip(),
        "upstream_runtime_gate": str(flags.get("upstream_runtime_gate") or "").strip(),
        "launch_claim_scope": launch_claim_scope,
        "shell_surface_impacted": shell_surface_impacted,
        "journeys_touched": _csv_list(flags.get("journeys_touched")),
        "visible_fact_provenance": _csv_list(flags.get("visible_fact_provenance")),
    }


def current_shell_metadata_findings(
    flags: dict[str, Any],
    *,
    track: str,
    sync_contract: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], dict[str, Any]]:
    metadata = current_shell_metadata(flags)
    if track != "CurrentShell":
        return [], [], metadata

    blockers: list[str] = []
    advisories: list[str] = []

    owner_lane = str(metadata["owner_lane"] or "")
    if not owner_lane:
        advisories.append("missing_owner_lane_advisory")
    elif owner_lane not in CURRENT_SHELL_OWNER_LANES:
        blockers.append(f"invalid_owner_lane:{owner_lane}")

    launch_claim_scope = str(metadata["launch_claim_scope"] or "")
    if launch_claim_scope and launch_claim_scope not in CURRENT_SHELL_LAUNCH_CLAIM_SCOPES:
        blockers.append(f"invalid_launch_claim_scope:{launch_claim_scope}")

    shell_surface_impacted = metadata["shell_surface_impacted"]
    if shell_surface_impacted not in {True, False, None}:
        blockers.append(f"invalid_shell_surface_impacted:{shell_surface_impacted}")

    upstream_runtime_gate = str(metadata["upstream_runtime_gate"] or "")
    contract = sync_contract or {}
    runtime_gate_ids = {str(item) for item in contract.get("runtime_gate_ids") or []}
    if upstream_runtime_gate and upstream_runtime_gate != "not_applicable" and runtime_gate_ids:
        if upstream_runtime_gate not in runtime_gate_ids:
            blockers.append(f"invalid_upstream_runtime_gate:{upstream_runtime_gate}")

    return sorted(set(blockers)), sorted(set(advisories)), metadata


def _string_blob(pr: dict[str, Any]) -> str:
    return "\n".join(str(pr.get(key) or "") for key in ("title", "headRefName", "body", "diff_text"))


def normalize_track(track: str) -> str:
    normalized = track.strip()
    aliases = {
        "FDB": "FoodDB",
        "FoodDB-WebSearch": "FoodDB",
        "FoodDB/WebSearch": "FoodDB",
        "FoodDB_WebSearch": "FoodDB",
        "Governance": "MergeGovernance",
        "GovernanceGuard": "MergeGovernance",
        "PLCE": "CurrentShell",
        "PL+CE": "CurrentShell",
        "PL_CE": "CurrentShell",
        "PL/CE": "CurrentShell",
        "PL-CE": "CurrentShell",
        "ProductLoop": "CurrentShell",
        "ProductLifecycleContextEngineering": "CurrentShell",
    }
    return aliases.get(normalized, normalized)


def infer_track(pr: dict[str, Any]) -> str:
    flags = extract_track_report(str(pr.get("body") or ""))
    explicit = str(flags.get("track") or "").strip()
    if explicit:
        return normalize_track(explicit)
    blob = "\n".join(str(pr.get(key) or "") for key in ("title", "headRefName")).lower()
    if "recommendation" in blob:
        return "RecommendationShadow"
    if "rescue" in blob:
        return "RescueShadow"
    if "proactive" in blob:
        return "ProactiveShadow"
    if "long-term" in blob or "long_term" in blob or "memory" in blob:
        return "LongTermContextLab"
    if "body-budget" in blob or "bodybudget" in blob or "calibration" in blob:
        return "BodyBudgetCalibration"
    if "fooddb" in blob or "food db" in blob or "websearch" in blob:
        return "FoodDB"
    if "currentshell" in blob or "current shell" in blob or "managerruntime" in blob or "appshell" in blob:
        return "CurrentShell"
    if "plce" in blob or "pl+ce" in blob or "webshell" in blob or "product page" in blob:
        return "CurrentShell"
    if "accurate-intake" in blob or "accurate intake" in blob:
        return "AccurateIntake"
    fallback_blob = _string_blob(pr).lower()
    if "recommendation" in fallback_blob:
        return "RecommendationShadow"
    if "rescue" in fallback_blob:
        return "RescueShadow"
    if "proactive" in fallback_blob:
        return "ProactiveShadow"
    if "long-term" in fallback_blob or "long_term" in fallback_blob or "memory" in fallback_blob:
        return "LongTermContextLab"
    return "unknown"


def _normalize_repo_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def normalize_pr_files(pr: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in pr.get("files") or []:
        if isinstance(item, str):
            normalized.append({"path": _normalize_repo_path(item), "additions": 0, "deletions": 0})
        elif isinstance(item, dict):
            normalized.append(
                {
                    "path": _normalize_repo_path(str(item.get("path") or "")),
                    "additions": int(item.get("additions") or 0),
                    "deletions": int(item.get("deletions") or 0),
                }
            )
    return normalized


def _files(pr: dict[str, Any]) -> list[dict[str, Any]]:
    return normalize_pr_files(pr)


def detect_contract_drift(pr: dict[str, Any]) -> list[str]:
    findings = list(pr.get("contract_findings") or [])
    text = "\n".join(str(pr.get(key) or "") for key in ("title", "headRefName", "body"))
    diff_text = str(pr.get("diff_text") or "")
    if diff_text:
        added_lines = "\n".join(line[1:] for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
        text = f"{text}\n{added_lines}"
    for code, pattern in STALE_CONTRACT_PATTERNS:
        if re.search(pattern, text):
            findings.append(code)
    return sorted(set(findings))


def _is_dependency_bump(pr: dict[str, Any]) -> bool:
    head = str(pr.get("headRefName") or "")
    title = str(pr.get("title") or "")
    return head.startswith("dependabot/") or title.lower().startswith("bump ")


def _mainline_status(*, pr: dict[str, Any], track: str, config: dict[str, Any]) -> str:
    if _is_dependency_bump(pr):
        return "dependency_bump"
    file_paths = [file["path"] for file in _files(pr)]
    if any(path.startswith("scripts/merge_governance/") for path in file_paths) or any(
        path in {".merge-governance.yml", ".github/workflows/merge-governance.yml"} for path in file_paths
    ):
        return "governance_guard"
    if track in set(config.get("mvp_mainline_tracks") or []):
        return "mvp_mainline"
    if track in set(config.get("future_shadow_tracks") or []):
        return "future_shadow"
    return "unknown"


def _stack_role(pr: dict[str, Any], prs: list[dict[str, Any]], *, main_branch: str) -> str:
    head = str(pr.get("headRefName") or "")
    base = str(pr.get("baseRefName") or "")
    heads = {str(item.get("headRefName") or "") for item in prs}
    has_parent = base != main_branch and base in heads
    has_child = any(str(item.get("baseRefName") or "") == head for item in prs)
    if has_parent and has_child:
        return "middle"
    if has_parent:
        return "leaf"
    if has_child:
        return "root"
    return "standalone"


def _stack_depth(pr: dict[str, Any], prs: list[dict[str, Any]], *, main_branch: str) -> int:
    base_by_head = {str(item.get("headRefName") or ""): str(item.get("baseRefName") or "") for item in prs}
    depth = 1
    base = str(pr.get("baseRefName") or "")
    seen: set[str] = set()
    while base and base != main_branch and base in base_by_head and base not in seen:
        seen.add(base)
        depth += 1
        base = base_by_head[base]
    return depth


def _stack_policy_status(*, stack_depth: int, config: dict[str, Any]) -> tuple[str, list[str]]:
    max_depth = int((config.get("size_budget") or {}).get("max_stack_depth") or 2)
    if stack_depth > max_depth:
        return "fail", [f"stack_depth_over_policy:{stack_depth}>{max_depth}"]
    return "pass", []


def _ci_status(pr: dict[str, Any], required_checks: list[str]) -> tuple[str, list[str]]:
    checks = pr.get("statusCheckRollup") or []
    blocking: list[str] = []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for check in checks:
        name = str(check.get("name") or "")
        by_name.setdefault(name, []).append(check)
    for required in required_checks:
        matches = by_name.get(required) or []
        if not matches:
            blocking.append(f"missing_required_check:{required}")
            continue
        for check in matches:
            status = str(check.get("status") or "").upper()
            conclusion = str(check.get("conclusion") or "").upper()
            if status != "COMPLETED" or not conclusion:
                blocking.append(f"pending_required_check:{required}")
            elif conclusion in FAIL_CONCLUSIONS or conclusion not in SUCCESS_CONCLUSIONS:
                blocking.append(f"failed_required_check:{required}")
    if any(reason.startswith("failed_required_check") for reason in blocking):
        return "fail", blocking
    if any(reason.startswith("pending_required_check") for reason in blocking):
        return "pending", blocking
    if blocking:
        return "incomplete", blocking
    return "pass", []


def _advisory_check_status(pr: dict[str, Any], advisory_checks: list[str]) -> tuple[str, list[str]]:
    checks = pr.get("statusCheckRollup") or []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for check in checks:
        name = str(check.get("name") or "")
        by_name.setdefault(name, []).append(check)
    findings: list[str] = []
    for advisory in advisory_checks:
        for check in by_name.get(advisory) or []:
            status = str(check.get("status") or "").upper()
            conclusion = str(check.get("conclusion") or "").upper()
            if status != "COMPLETED" or not conclusion:
                findings.append(f"pending_advisory_check:{advisory}")
            elif conclusion in FAIL_CONCLUSIONS or conclusion not in SUCCESS_CONCLUSIONS:
                findings.append(f"failed_advisory_check:{advisory}")
    if any(item.startswith("failed_advisory_check") for item in findings):
        return "fail", findings
    if any(item.startswith("pending_advisory_check") for item in findings):
        return "pending", findings
    return "pass", findings


def _base_drift_status(pr: dict[str, Any], contract_findings: list[str]) -> tuple[str, list[str]]:
    if contract_findings:
        return "stale_contract_detected", [f"contract_drift:{finding}" for finding in contract_findings]
    head_contains_main = pr.get("head_contains_main")
    if head_contains_main is False:
        return "stale_to_main", ["head_branch_does_not_contain_origin_main"]
    if head_contains_main is None:
        return "stale_to_main", ["head_branch_freshness_unknown"]
    return "current", []


def _track_report_status(flags: dict[str, Any]) -> tuple[str, list[str]]:
    missing = [key for key in REQUIRED_TRACK_REPORT_KEYS if key not in flags]
    if missing:
        return "missing", [f"missing_track_report_key:{key}" for key in missing]
    return "pass", []


def _future_forbidden_flags(flags: dict[str, Any], config: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for item in config.get("forbidden_future_runtime_effects") or []:
        for key, forbidden_value in dict(item).items():
            if flags.get(key) is forbidden_value:
                findings.append(f"forbidden_future_runtime_effect:{key}")
    return findings


def evaluate_sidecar_activation(
    *,
    track: str,
    mainline_status: str,
    files: list[dict[str, Any]],
    flags: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, str, list[str]]:
    if mainline_status != "future_shadow":
        return "pass", "inactive", []
    findings = _future_forbidden_flags(flags, config)
    runtime_status = "inactive"
    for file in files:
        path = str(file["path"])
        if path.startswith("app/rescue/fixtures/"):
            findings.append("rescue_fixture_under_active_app_policy")
        if path.startswith("app/runtime/application/"):
            if track == "ProactiveShadow" and path in PROACTIVE_SHADOW_ALLOWED_RUNTIME_APPLICATION_PATHS:
                runtime_status = "inactive"
            else:
                runtime_status = "suspicious"
        if any(path == pattern or path.startswith(pattern) for pattern in FUTURE_ACTIVE_SURFACE_PATTERNS):
            if not path.startswith("app/runtime/application/"):
                runtime_status = "active"
                findings.append(f"future_shadow_touches_active_surface:{path}")
    if any(reason.startswith("forbidden_future_runtime_effect") for reason in findings):
        runtime_status = "active"
    if findings:
        return "fail", runtime_status, sorted(set(findings))
    return "pass", runtime_status, []


def evaluate_deterministic_boundary(*, track: str, pr: dict[str, Any]) -> tuple[str, list[str]]:
    text = _string_blob(pr).lower()
    manager_required_markers = (
        "manager_selection_required",
        "manager selection required",
        "manager selection boundary",
        "selection_owner",
    )
    if track == "RecommendationShadow" and "top_pick" in text and not any(
        marker in text for marker in manager_required_markers
    ):
        return "fail", ["recommendation_shadow_top_pick_without_manager_selection"]
    return "pass", []


def evaluate_size_budget(
    *,
    mainline_status: str,
    additions: int,
    files: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[str, list[str]]:
    budget = dict(config.get("size_budget") or {})
    if mainline_status == "future_shadow" and additions > int(budget.get("future_shadow_merge_max_additions") or 250):
        return "warning", [f"future_shadow_additions_over_budget:{additions}"]
    if mainline_status == "mvp_mainline" and additions > int(budget.get("mvp_mainline_max_additions") or 600):
        return "warning", [f"mvp_mainline_additions_over_budget:{additions}"]
    fat_files = [file["path"] for file in files if int(file.get("additions") or 0) > 800]
    if fat_files:
        return "warning", [f"large_file_additions:{path}" for path in fat_files]
    return "pass", []


def _is_guard_only_future_pr(*, files: list[dict[str, Any]], additions: int, config: dict[str, Any]) -> bool:
    max_additions = int((config.get("size_budget") or {}).get("future_shadow_merge_max_additions") or 250)
    if additions > max_additions:
        return False
    if not files:
        return False
    for file in files:
        path = str(file["path"]).lower()
        if path.startswith("tests/"):
            continue
        if path.startswith("docs/"):
            continue
        if any(token in path for token in GUARD_OR_CONTRACT_TOKENS):
            continue
        return False
    return True


def _merge_readiness_status(
    *,
    ci_status: str,
    base_drift_status: str,
    boundary_status: str,
    deterministic_boundary_status: str,
    track_report_status: str,
    metadata_blockers: list[str],
    mainline_status: str,
) -> str:
    if ci_status in {"fail", "pending", "incomplete"}:
        return "blocked"
    if boundary_status == "fail" or deterministic_boundary_status == "fail":
        return "blocked"
    if metadata_blockers:
        return "blocked"
    if track_report_status == "missing" and mainline_status not in {"governance_guard", "dependency_bump"}:
        return "blocked"
    if base_drift_status != "current":
        return "stale"
    return "ready_for_human_queue_review"


def build_matrix_from_prs(prs: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    required_checks = [str(item) for item in config.get("required_checks") or []]
    advisory_checks = [str(item) for item in config.get("advisory_checks") or []]
    main_branch = str(config.get("main_branch") or "main")
    sync_contract = load_current_shell_sync_contract()
    for pr in sorted(prs, key=lambda item: int(item.get("number") or 0), reverse=True):
        flags = extract_track_report(str(pr.get("body") or ""))
        track = infer_track(pr)
        metadata_blockers, metadata_advisories, metadata = current_shell_metadata_findings(
            flags,
            track=track,
            sync_contract=sync_contract,
        )
        files = _files(pr)
        additions = int(pr.get("additions") or sum(int(file.get("additions") or 0) for file in files))
        mainline_status = _mainline_status(pr=pr, track=track, config=config)
        stack_role = _stack_role(pr, prs, main_branch=main_branch)
        stack_depth = _stack_depth(pr, prs, main_branch=main_branch)
        stack_policy_status, stack_blockers = _stack_policy_status(stack_depth=stack_depth, config=config)
        ci_status, ci_blockers = _ci_status(pr, required_checks)
        advisory_status, advisory_findings = _advisory_check_status(pr, advisory_checks)
        contract_findings = detect_contract_drift(pr)
        base_drift_status, drift_blockers = _base_drift_status(pr, contract_findings)
        if mainline_status in {"dependency_bump", "governance_guard"}:
            track_report_status, track_report_blockers = "pass", []
        else:
            track_report_status, track_report_blockers = _track_report_status(flags)
        boundary_status, runtime_activation_status, boundary_blockers = evaluate_sidecar_activation(
            track=track,
            mainline_status=mainline_status,
            files=files,
            flags=flags,
            config=config,
        )
        if boundary_status == "pass" and track_report_status == "missing":
            boundary_status = "needs_review"
        if metadata_blockers and boundary_status == "pass":
            boundary_status = "fail"
        deterministic_status, deterministic_blockers = evaluate_deterministic_boundary(track=track, pr=pr)
        fat_file_status, fat_blockers = evaluate_size_budget(
            mainline_status=mainline_status,
            additions=additions,
            files=files,
            config=config,
        )
        advisory_blockers = sorted(set(advisory_findings + metadata_advisories))
        blockers = sorted(
            set(
                ci_blockers
                + drift_blockers
                + track_report_blockers
                + boundary_blockers
                + deterministic_blockers
                + fat_blockers
                + stack_blockers
                + metadata_blockers
            )
        )
        merge_readiness_status = _merge_readiness_status(
            ci_status=ci_status,
            base_drift_status=base_drift_status,
            boundary_status=boundary_status,
            deterministic_boundary_status=deterministic_status,
            track_report_status=track_report_status,
            metadata_blockers=metadata_blockers,
            mainline_status=mainline_status,
        )
        entries.append(
            {
                "pr_number": int(pr.get("number") or 0),
                "title": str(pr.get("title") or ""),
                "url": str(pr.get("url") or ""),
                "track": track,
                "owner_lane": metadata.get("owner_lane") or "",
                "slice_class": metadata.get("slice_class") or "",
                "pass_type": metadata.get("pass_type") or "",
                "upstream_runtime_gate": metadata.get("upstream_runtime_gate") or "",
                "launch_claim_scope": metadata.get("launch_claim_scope") or "",
                "shell_surface_impacted": metadata.get("shell_surface_impacted"),
                "journeys_touched": metadata.get("journeys_touched") or [],
                "visible_fact_provenance": metadata.get("visible_fact_provenance") or [],
                "base_branch": str(pr.get("baseRefName") or ""),
                "head_branch": str(pr.get("headRefName") or ""),
                "stack_role": stack_role,
                "stack_depth": stack_depth,
                "mainline_status": mainline_status,
                "ci_status": ci_status,
                "advisory_check_status": advisory_status,
                "base_drift_status": base_drift_status,
                "current_shell_metadata_status": "fail" if metadata_blockers else ("advisory" if metadata_advisories else "pass"),
                "boundary_status": boundary_status,
                "deterministic_boundary_status": deterministic_status,
                "runtime_activation_status": runtime_activation_status,
                "fat_file_status": fat_file_status,
                "merge_readiness_status": merge_readiness_status,
                "blocking_reasons": blockers,
                "advisories": advisory_blockers,
                "additions": additions,
                "deletions": int(pr.get("deletions") or 0),
                "changed_files": int(pr.get("changedFiles") or len(files)),
                "is_draft": bool(pr.get("isDraft")),
                "merge_state_status": str(pr.get("mergeStateStatus") or ""),
            }
        )
    return {
        "artifact_type": "merge_governance_advisory",
        "main_branch": main_branch,
        "entry_count": len(entries),
        "merge_readiness_counts": _counts(entry["merge_readiness_status"] for entry in entries),
        "entries": entries,
    }


def _counts(items: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[str(item)] = counts.get(str(item), 0) + 1
    return dict(sorted(counts.items()))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Merge Governance Advisory",
        "",
        f"- Main branch: `{report.get('main_branch')}`",
        f"- Entry count: `{report.get('entry_count')}`",
        f"- Merge readiness counts: `{json.dumps(report.get('merge_readiness_counts') or {}, sort_keys=True)}`",
        "",
        "| # | Track | Status | Readiness | Blocking reasons | Advisories |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in report.get("entries") or []:
        status = (
            f"{entry['mainline_status']} / {entry['ci_status']} / "
            f"{entry['base_drift_status']} / {entry['boundary_status']}"
        )
        blockers = ", ".join(entry.get("blocking_reasons") or []) or "-"
        advisories = ", ".join(entry.get("advisories") or []) or "-"
        lines.append(
            f"| #{entry['pr_number']} | `{entry['track']}` | `{status}` | "
            f"`{entry['merge_readiness_status']}` | {blockers} | {advisories} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a PR merge debt matrix without merging branches.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--input-json", type=Path, help="Optional fixture/open PR JSON. If omitted, gh pr list is used.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--skip-diff-scan", action="store_true")
    parser.add_argument("--fail-on-blocking", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.input_json:
        if not args.input_json.exists():
            print(json.dumps({"error": "input_json_not_found", "path": str(args.input_json)}, ensure_ascii=False))
            return 2
        prs = json.loads(args.input_json.read_text(encoding="utf-8"))
    else:
        prs = collect_open_prs(config=config, include_diffs=not args.skip_diff_scan, limit=args.limit)
    report = build_matrix_from_prs(prs, config)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json_report": str(args.json_out), "markdown_report": str(args.md_out)}, ensure_ascii=False))
    if args.fail_on_blocking and any(entry["merge_readiness_status"] != "ready_for_human_queue_review" for entry in report["entries"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
