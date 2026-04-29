from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROMPT_TEMPLATE_DIR = ROOT / "docs" / "agent" / "autonomy-prompts"
SCHEMA_DIR = ROOT / "docs" / "agent" / "autonomy-schemas"
DEFAULT_RUN_ROOT = ROOT / "artifacts" / "recovery" / "b1_autorun"
DEFAULT_NEXT_LIVE_TARGET = "B1-004 real Pass 2 trace/provider contract completeness"
LATEST_READINESS_PATH = ROOT / "artifacts" / "wave1_phase_b_minimal_tool_loop_readiness.json"
LATEST_FULL_SMOKE_GLOB = "wave1_phase_b_minimal_tool_loop_smoke_*.json"
ROLE_WRAPPER_PATH = ROOT / "scripts" / "run_codex_exec_with_prompt.py"
PYTHON_BIN = sys.executable
DEFAULT_RUN_PROFILE_ID = "overnight_useful_b1"
DEFAULT_ROLE_TIMEOUT_SECONDS_BY_ROLE = {
    "planner": 180,
    "evaluator": 180,
    "worker": 300,
    "verifier": 240,
}
RUN_PROFILES = {
    DEFAULT_RUN_PROFILE_ID: {
        "phase_boundary": "B-1 only",
        "max_slices": 4,
        "max_autonomous_repair_attempts_per_family": 3,
        "planner_timeout_seconds": 180,
        "evaluator_timeout_seconds": 180,
        "worker_timeout_seconds": {
            "ordinary_implementation_slice": 300,
            "provider_runtime_repair_slice": 600,
        },
        "verifier_timeout_seconds": 240,
    }
}
PROVIDER_CONNECTIVITY_LANE_ID = "provider_connectivity_local_runtime_repair_v1"
PROVIDER_CONNECTIVITY_VERIFICATION_COMMANDS = (
    "$env:PYTHONPATH='.'; pytest tests/test_builderspace_adapter.py -q -k \"connect_error or timeout or retry\"",
    "$env:PYTHONPATH='.'; pytest tests/test_wave1_phase_b_minimal_tool_loop_smoke.py -q -k \"targeted_connect_error or persistent_connect_error or full_connect_error\"",
    "python scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py --mode natural-probe --cases B1-004 --provider-profile-id builderspace-grok-4-fast-b1004-probe",
    "python scripts/verify_wave1_phase_b_tool_loop_readiness.py --phase-b-report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json",
)
PROVIDER_CONNECTIVITY_LANE_IN_SCOPE_FILES = (
    "app/providers/builderspace_adapter.py",
    "app/providers/builderspace_session.py",
    "app/providers/builderspace_parsing.py",
    "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
    "tests/test_builderspace_adapter.py",
    "tests/test_wave1_phase_b_minimal_tool_loop_smoke.py",
)
PROVIDER_CONNECTIVITY_LANE_FORBIDDEN_CHANGES = (
    "logged/draft changes",
    "clarification vs estimate policy changes",
    "prompt-semantic workarounds",
    "parser recovery widening that hides transport failure",
    "global model/provider default switch",
    "B-2 retrieval/evidence changes",
    "app/runtime/**",
)
SELF_HEALABLE_BLOCKER_FAMILIES = {
    "provider_connectivity",
    "model_profile_mismatch",
    "structured_transport_incompatibility",
    "timeout_retry_miscalibration",
    "targeted_probe_routing_gap",
    "artifact_attribution_gap",
}
STOP_CLASS_VALUES = {
    "completed_slice_continue_allowed",
    "human_review_required",
    "runtime_blocker_unchanged",
    "runtime_blocker_stalled",
    "runtime_budget_exhausted",
    "role_timeout",
    "malformed_role_output",
    "dirty_tree_stop",
    "semantic_boundary_touched",
    "generic_stop",
}

ROLE_ORDER = ("planner", "evaluator", "worker", "verifier")
PROMPT_FILES = {
    "planner": "B1_PLANNER_PROMPT.md",
    "evaluator": "B1_EVALUATOR_PROMPT.md",
    "worker": "B1_WORKER_PROMPT.md",
    "verifier": "B1_VERIFIER_PROMPT.md",
}
SCHEMA_FILES = {
    "planner": "planner_result.schema.json",
    "evaluator": "evaluator_result.schema.json",
    "worker": "worker_result.schema.json",
    "verifier": "verifier_result.schema.json",
    "checkpoint": "checkpoint.schema.json",
}
ROLE_OUTPUT_FILENAME_RE = re.compile(r"^(?P<round>\d{2})_(?P<role>planner|evaluator|worker|verifier)\.json$")


class RoleOutputValidationError(ValueError):
    pass


class RoleExecutionTimeoutError(TimeoutError):
    pass


def _build_role_timeout_overrides_from_args(args: argparse.Namespace) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for role in ROLE_ORDER:
        value = getattr(args, f"{role}_timeout_seconds", None)
        if value is not None:
            overrides[role] = value
    return overrides


def _get_run_profile(run_profile_id: str | None) -> dict[str, Any]:
    resolved = run_profile_id or DEFAULT_RUN_PROFILE_ID
    if resolved not in RUN_PROFILES:
        raise RoleOutputValidationError(f"Unsupported run profile: {resolved}")
    return {"run_profile_id": resolved, **RUN_PROFILES[resolved]}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_json_object_from_cli_output(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise RoleOutputValidationError("CLI role output was empty.")

    decoder = json.JSONDecoder()

    def _decode_object(candidate: str) -> dict[str, Any] | None:
        try:
            value, _end = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict):
            return value
        raise RoleOutputValidationError("CLI role output must decode to a JSON object.")

    if stripped.startswith("{"):
        value = _decode_object(stripped)
        if value is not None:
            return value
    fenced_match = re.search(r"```json\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        value = _decode_object(fenced_match.group(1))
        if value is not None:
            return value
    brace_index = stripped.find("{")
    if brace_index != -1:
        value = _decode_object(stripped[brace_index:])
        if value is not None:
            return value
    raise RoleOutputValidationError("CLI role output did not contain a parseable JSON object.")


def _latest_full_smoke_path() -> Path | None:
    matches = sorted((ROOT / "artifacts").glob(LATEST_FULL_SMOKE_GLOB), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _merge_unique_items(*groups: Sequence[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item not in seen:
                merged.append(item)
                seen.add(item)
    return merged


def _provider_connectivity_lane_bundle() -> dict[str, Any]:
    return {
        "repair_lane_id": PROVIDER_CONNECTIVITY_LANE_ID,
        "verification_commands": list(PROVIDER_CONNECTIVITY_VERIFICATION_COMMANDS),
        "in_scope_files": list(PROVIDER_CONNECTIVITY_LANE_IN_SCOPE_FILES),
        "forbidden_changes": list(PROVIDER_CONNECTIVITY_LANE_FORBIDDEN_CHANGES),
    }


def _canonical_lane_bundle(*, blocker_family: str, repair_scope: str) -> dict[str, Any] | None:
    normalized_family = _normalize_blocker_family_name(blocker_family)
    if normalized_family == "provider_connectivity" and repair_scope == "local_runtime_repair":
        return _provider_connectivity_lane_bundle()
    return None


def _json_type_matches(expected: str, value: Any) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate_against_schema(value: Any, schema: dict[str, Any], *, path: str = "$") -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_json_type_matches(type_name, value) for type_name in allowed_types):
            allowed = ", ".join(str(item) for item in allowed_types)
            return [f"{path}: expected type {allowed}, got {type(value).__name__}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum {schema['enum']!r}")
        return errors

    if isinstance(value, dict):
        required = list(schema.get("required") or [])
        properties = dict(schema.get("properties") or {})
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: missing required field")
        additional_allowed = schema.get("additionalProperties", True)
        if additional_allowed is False:
            unknown_keys = sorted(set(value.keys()) - set(properties.keys()))
            for key in unknown_keys:
                errors.append(f"{path}.{key}: additional property not allowed")
        for key, child_schema in properties.items():
            if key in value:
                errors.extend(_validate_against_schema(value[key], child_schema, path=f"{path}.{key}"))

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        for index, item in enumerate(value):
            errors.extend(_validate_against_schema(item, item_schema, path=f"{path}[{index}]"))

    return errors


def validate_role_output(role: str, payload: dict[str, Any]) -> dict[str, Any]:
    schema_name = SCHEMA_FILES[role]
    schema = _json_load(SCHEMA_DIR / schema_name)
    errors = _validate_against_schema(payload, schema)
    if role == "planner":
        external_refs = list(payload.get("external_refs_checked") or [])
        omitted_reason = payload.get("external_research_omitted_reason")
        if not external_refs and not (isinstance(omitted_reason, str) and omitted_reason.strip()):
            errors.append("$.external_research_omitted_reason: non-empty reason required when external_refs_checked is empty")
    if role == "evaluator":
        attack_findings = dict(payload.get("attack_findings") or {})
        must_block = list(attack_findings.get("must_block") or [])
        approve_condition = list(attack_findings.get("approve_condition") or [])
        verdict = payload.get("verdict")
        narrowed_boundary = payload.get("narrowed_boundary")
        conditions = list(payload.get("conditions") or [])

        if must_block and verdict != "reject":
            errors.append("$.verdict: must be 'reject' when attack_findings.must_block is non-empty")
        if verdict == "reject" and not must_block:
            errors.append("$.attack_findings.must_block: reject requires at least one must_block finding")
        if approve_condition and verdict != "approve_with_conditions":
            errors.append("$.verdict: must be 'approve_with_conditions' when attack_findings.approve_condition is non-empty")
        if verdict == "approve_with_conditions" and not approve_condition:
            errors.append("$.attack_findings.approve_condition: approve_with_conditions requires at least one approve_condition")
        if verdict == "approve_with_narrower_boundary" and not (isinstance(narrowed_boundary, str) and narrowed_boundary.strip()):
            errors.append("$.narrowed_boundary: non-empty narrowed boundary required for approve_with_narrower_boundary")
        if conditions and verdict not in {"approve_with_conditions", "approve_with_narrower_boundary"}:
            errors.append("$.conditions: conditions are only valid for approve_with_conditions or approve_with_narrower_boundary")
    if role == "worker":
        blocker_found = payload.get("blocker_found")
        status = payload.get("status")
        if blocker_found is not None and status != "blocked":
            errors.append("$.status: must be 'blocked' when blocker_found is present")
    if role == "verifier":
        result_class = payload.get("result_class")
        blocker_status = payload.get("blocker_status")
        if result_class == "fixed" and blocker_status not in {"moved", "cleared"}:
            errors.append("$.blocker_status: fixed requires blocker_status to be 'moved' or 'cleared'")
    if errors:
        raise RoleOutputValidationError("; ".join(errors))
    return payload


def _git_run(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def perform_preflight(*, workspace: Path, preflight_dir: Path, dirty_policy: str) -> dict[str, Any]:
    preflight_dir.mkdir(parents=True, exist_ok=True)
    status_proc = _git_run(workspace, "status", "--short", "--branch")
    status_text = status_proc.stdout
    status_lines = [line for line in status_text.splitlines() if line.strip()]
    dirty = any(not line.startswith("##") for line in status_lines)

    report = {
        "generated_at_utc": _utc_now(),
        "workspace": str(workspace),
        "dirty": dirty,
        "dirty_policy": dirty_policy,
        "git_status_exit_code": status_proc.returncode,
        "git_status_stdout": status_text,
        "action": "continue",
    }

    (preflight_dir / "git_status.txt").write_text(status_text, encoding="utf-8")

    if not dirty:
        _json_dump(preflight_dir / "dirty_tree_report.json", report)
        return report

    if dirty_policy == "stop":
        report["action"] = "stop"
        _json_dump(preflight_dir / "dirty_tree_report.json", report)
        return report

    diff_proc = _git_run(workspace, "diff", "--no-ext-diff")
    cached_proc = _git_run(workspace, "diff", "--cached", "--no-ext-diff")
    untracked_proc = _git_run(workspace, "ls-files", "--others", "--exclude-standard")

    (preflight_dir / "git_diff.patch").write_text(diff_proc.stdout, encoding="utf-8")
    (preflight_dir / "git_cached_diff.patch").write_text(cached_proc.stdout, encoding="utf-8")
    (preflight_dir / "git_untracked.txt").write_text(untracked_proc.stdout, encoding="utf-8")

    report["action"] = "snapshot"
    report["snapshot_files"] = [
        "git_status.txt",
        "git_diff.patch",
        "git_cached_diff.patch",
        "git_untracked.txt",
        "dirty_tree_report.json",
    ]
    _json_dump(preflight_dir / "dirty_tree_report.json", report)
    return report


def _default_noop_role_output(role: str, *, run_id: str, slice_id: str, current_full_smoke: str | None) -> dict[str, Any]:
    if role == "planner":
        return {
            "run_id": run_id,
            "slice_id": slice_id,
            "first_blocker": {
                "code": "dry_run_only",
                "detail": "No live role provider configured; this run only validates the detached loop infrastructure.",
            },
            "repo_truth_refs": [
                "docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md",
                "docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md",
            ],
            "external_refs_checked": [
                "https://docs.anthropic.com/en/docs/claude-code/sub-agents",
                "https://platform.openai.com/docs/guides/evaluation-best-practices",
            ],
            "external_research_required": True,
            "external_research_omitted_reason": None,
            "in_scope_files": [
                "scripts/run_b1_cli_autorun.py",
                "scripts/run_codex_exec_with_prompt.py",
                "docs/agent/autonomy-prompts/",
                "docs/agent/autonomy-schemas/",
            ],
            "out_of_scope": [
                "app/runtime/**",
                "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
            ],
            "verification_commands": [
                "python -m pytest tests\\test_run_codex_exec_with_prompt.py tests\\test_b1_cli_autorun.py -q",
                "python scripts\\check_markdown_encoding.py --policy-docs --require-bom",
            ],
            "stop_conditions": [
                "human_review_required",
                "semantic_ambiguity_reached",
                "ready_for_phase_b1_implementation",
            ],
        }
    if role == "evaluator":
        return {
            "verdict": "approve",
            "architecture_rationale": "Dry-run infrastructure adds audit seams without changing B-1 runtime behavior.",
            "ux_journey_rationale": "No live UX behavior changes are introduced in this slice.",
            "narrowed_boundary": None,
            "human_review_required": False,
            "attack_findings": {
                "must_block": [],
                "approve_condition": [],
                "cleanup_debt": [
                    "Keep this slice infrastructure-only.",
                    "Do not touch live B-1 runtime or product semantics.",
                ],
            },
            "conditions": [],
            "approval_rationale": "Approve because this remains dry-run infrastructure with explicit checkpoints.",
            "checked_context_packs": [
                "UX / Product Journey",
                "Product Semantics",
                "Architecture Transition",
                "Current Repo Truth",
            ],
            "architecture_boundary_touched": ["eval_only"],
        }
    if role == "worker":
        return {
            "status": "completed",
            "files_changed": [],
            "commands_run": [
                "dry-run only",
            ],
            "blocker_found": None,
            "conditions_followed": [],
            "out_of_scope_changes_avoided": True,
            "notes": f"Prepared detached loop scaffolding only. Latest full smoke path: {current_full_smoke or 'not_found'}",
        }
    if role == "verifier":
        return {
            "result_class": "verification_incomplete",
            "tests_run": [
                {
                    "command": "dry-run only",
                    "result": "not_run",
                }
            ],
            "artifact_paths": [],
            "readiness_delta": "none",
            "conditions_verified": [],
            "blocker_status": "not_evaluable",
            "next_safe_action": "stop",
            "human_review_required": False,
        }
    raise ValueError(f"Unsupported role: {role}")


def _load_mock_role_output(mock_scenario: dict[str, Any], *, round_index: int, role: str) -> dict[str, Any]:
    rounds = list(mock_scenario.get("rounds") or [])
    if round_index >= len(rounds):
        raise RoleOutputValidationError(f"mock scenario missing round {round_index}")
    round_payload = rounds[round_index]
    if role not in round_payload:
        raise RoleOutputValidationError(f"mock scenario missing role {role!r} in round {round_index}")
    return dict(round_payload[role])


def invoke_live_cli_role(*, role: str, prompt_path: Path, workspace: Path, timeout_seconds: int) -> dict[str, Any]:
    cmd = [
        PYTHON_BIN,
        str(ROLE_WRAPPER_PATH),
        "--prompt-file",
        str(prompt_path),
        "--cd",
        str(workspace),
        "--mode",
        role,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RoleExecutionTimeoutError(f"CLI role {role} timed out after {timeout_seconds}s") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        detail = stderr or stdout or f"wrapper exited {proc.returncode}"
        raise RoleOutputValidationError(f"CLI role {role} failed: {detail}")
    return extract_json_object_from_cli_output(proc.stdout)


def _render_prompt_snapshot(role: str, *, context: dict[str, Any]) -> str:
    template_text = _read_text(PROMPT_TEMPLATE_DIR / PROMPT_FILES[role])
    context_block = json.dumps(context, ensure_ascii=False, indent=2)
    return (
        f"{template_text.rstrip()}\n\n"
        "## Run Context Snapshot\n\n"
        "```json\n"
        f"{context_block}\n"
        "```\n"
    )


def _write_prompt_snapshot(prompts_dir: Path, *, round_index: int, role: str, prompt_text: str) -> Path:
    path = prompts_dir / f"{round_index:02d}_{role}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt_text, encoding="utf-8")
    return path


def _write_role_output(outputs_dir: Path, *, round_index: int, role: str, payload: dict[str, Any]) -> Path:
    path = outputs_dir / f"{round_index:02d}_{role}.json"
    _json_dump(path, payload)
    return path


def _read_existing_run_state(*, run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    ledger_path = run_dir / "ledger.json"
    outputs_dir = run_dir / "outputs"

    if not manifest_path.exists():
        raise RoleOutputValidationError(f"resume requested but manifest is missing: {manifest_path}")
    if not ledger_path.exists():
        raise RoleOutputValidationError(f"resume requested but ledger is missing: {ledger_path}")

    manifest = _json_load(manifest_path)
    ledger = _json_load(ledger_path)

    outputs_by_round: dict[int, dict[str, Path]] = {}
    if outputs_dir.exists():
        for path in sorted(outputs_dir.glob("*.json")):
            match = ROLE_OUTPUT_FILENAME_RE.match(path.name)
            if not match:
                continue
            round_index = int(match.group("round"))
            role = match.group("role")
            outputs_by_round.setdefault(round_index, {})[role] = path

    if not outputs_by_round:
        return {
            "manifest": manifest,
            "ledger": ledger,
            "round_index": 0,
            "slice_id": None,
            "next_role": "planner",
            "checkpoint_pending": False,
            "role_outputs": {},
            "output_paths": {},
            "previous_artifact_path": None,
            "planner_scope": {
                "in_scope_files": [],
                "verification_commands": [],
                "stop_conditions": [],
                "out_of_scope": [],
            },
            "narrowed_boundary": "",
            "evaluator_conditions": [],
        }

    round_index = max(outputs_by_round)
    round_outputs = outputs_by_round[round_index]
    role_outputs: dict[str, dict[str, Any]] = {}
    output_paths: dict[str, str] = {}

    for role in ROLE_ORDER:
        if role not in round_outputs:
            continue
        payload = _json_load(round_outputs[role])
        validate_role_output(role, payload)
        role_outputs[role] = payload
        output_paths[role] = str(round_outputs[role])

    completed_roles = [role for role in ROLE_ORDER if role in role_outputs]
    next_role = next((role for role in ROLE_ORDER if role not in role_outputs), None)
    last_completed_role = completed_roles[-1] if completed_roles else None
    planner_result = role_outputs.get("planner", {})
    evaluator_result = role_outputs.get("evaluator", {})
    slice_id = planner_result.get("slice_id")

    return {
        "manifest": manifest,
        "ledger": ledger,
        "round_index": round_index,
        "slice_id": slice_id,
        "next_role": next_role,
        "checkpoint_pending": next_role is None,
        "role_outputs": role_outputs,
        "output_paths": output_paths,
        "previous_artifact_path": output_paths.get(last_completed_role) if last_completed_role else None,
        "planner_scope": {
            "in_scope_files": list(planner_result.get("in_scope_files", [])),
            "verification_commands": list(planner_result.get("verification_commands", [])),
            "stop_conditions": list(planner_result.get("stop_conditions", [])),
            "out_of_scope": list(planner_result.get("out_of_scope", [])),
        },
        "narrowed_boundary": evaluator_result.get("narrowed_boundary") or "",
        "evaluator_conditions": list(evaluator_result.get("conditions") or []),
    }


def _load_latest_truth() -> dict[str, Any]:
    return {
        "latest_readiness_path": str(LATEST_READINESS_PATH) if LATEST_READINESS_PATH.exists() else None,
        "latest_full_smoke_path": str(_latest_full_smoke_path()) if _latest_full_smoke_path() else None,
    }


def _load_existing_summaries(summaries_dir: Path) -> list[dict[str, Any]]:
    if not summaries_dir.exists():
        return []
    summaries: list[dict[str, Any]] = []
    for path in sorted(summaries_dir.glob("*.json")):
        if path.name == "latest_summary.json":
            continue
        summaries.append(_json_load(path))
    return summaries


def _classify_blocker_family(*payloads: dict[str, Any] | None) -> str:
    explicit_hints: list[str] = []
    text_parts: list[str] = []
    for payload in payloads:
        if not payload:
            continue
        blocker_family = payload.get("blocker_family")
        if blocker_family is not None:
            explicit_hints.append(str(blocker_family))
        repair_lane_id = payload.get("repair_lane_id")
        if repair_lane_id is not None:
            explicit_hints.append(str(repair_lane_id))
        blocker = payload.get("first_blocker") or payload.get("blocker_found")
        if isinstance(blocker, dict):
            blocker_code = str(blocker.get("code", ""))
            explicit_hints.append(blocker_code)
            text_parts.append(blocker_code)
            text_parts.append(str(blocker.get("detail", "")))
        text_parts.append(str(payload.get("readiness_delta", "")))
        text_parts.append(str(payload.get("notes", "")))

    explicit_stack = " ".join(explicit_hints).lower()
    if any(token in explicit_stack for token in ["provider_connectivity", "provider_runtime", "connecterror", "connect_error", "connectivity"]):
        return "provider_connectivity"
    if any(token in explicit_stack for token in ["model_profile_mismatch", "profile_mismatch", "candidate_matrix"]):
        return "model_profile_mismatch"
    if any(token in explicit_stack for token in ["structured_transport", "structured_output", "json_schema", "tool_choice", "transport_incompatibility"]):
        return "structured_transport_incompatibility"
    if any(token in explicit_stack for token in ["timeout_retry", "timeout", "retry", "backoff"]):
        return "timeout_retry_miscalibration"
    if any(token in explicit_stack for token in ["probe_routing", "targeted_probe_routing", "profile_routing"]):
        return "targeted_probe_routing_gap"
    if any(token in explicit_stack for token in ["artifact_attribution", "trace_attribution", "trace_missing"]):
        return "artifact_attribution_gap"
    if any(token in explicit_stack for token in ["product_semantics", "semantic_boundary", "clarification_vs_estimate", "logged_draft", "b-2"]):
        return "product_semantics"

    haystack = " ".join(text_parts).lower()

    if any(token in haystack for token in ["connecterror", "connect error", "provider_runtime", "provider runtime", "connectivity", "network", "transport instability"]):
        return "provider_connectivity"
    if any(token in haystack for token in ["profile mismatch", "model profile", "candidate matrix"]):
        return "model_profile_mismatch"
    if any(token in haystack for token in ["structured output", "json_schema", "tool_choice", "structured transport", "transport incompatibility", "parser recovery"]):
        return "structured_transport_incompatibility"
    if any(token in haystack for token in ["timeout", "retry", "backoff"]):
        return "timeout_retry_miscalibration"
    if any(token in haystack for token in ["routing", "targeted probe", "probe route", "profile route"]):
        return "targeted_probe_routing_gap"
    if any(token in haystack for token in ["attribution", "trace missing", "trace attribution", "completed trace"]):
        return "artifact_attribution_gap"
    if any(token in haystack for token in ["semantic", "logged", "draft", "no-mutation", "mutation", "clarification", "estimate", "b-2", "retrieval", "packet"]):
        return "product_semantics"
    return "unknown"


def _normalize_blocker_family_name(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return "unknown"
    if normalized in SELF_HEALABLE_BLOCKER_FAMILIES:
        return normalized
    if normalized in {"provider_runtime", "provider_runtime_blocker", "provider_runtime_connect_error", "provider_connect_error"}:
        return "provider_connectivity"
    if normalized in {"structured_transport", "transport_incompatibility"}:
        return "structured_transport_incompatibility"
    if normalized in {"timeout_retry", "timeout_retry_runtime"}:
        return "timeout_retry_miscalibration"
    if normalized in {"profile_routing", "probe_routing", "targeted_probe_routing"}:
        return "targeted_probe_routing_gap"
    if normalized in {"artifact_attribution", "trace_attribution"}:
        return "artifact_attribution_gap"
    if normalized in {"product_semantics", "semantics"}:
        return "product_semantics"
    return normalized


def _derive_evidence_tier(
    *,
    attempt_index: int,
    planner_result: dict[str, Any],
    worker_result: dict[str, Any],
    verifier_result: dict[str, Any],
) -> int:
    if verifier_result.get("blocker_status") in {"moved", "cleared"} or verifier_result.get("result_class") == "fixed":
        return 3

    corroborating_signals = 0
    if planner_result.get("first_blocker"):
        corroborating_signals += 1
    if worker_result.get("blocker_found"):
        corroborating_signals += 1
    if list(verifier_result.get("artifact_paths") or []):
        corroborating_signals += 1
    elif list(verifier_result.get("tests_run") or []):
        corroborating_signals += 1
    if attempt_index > 1:
        corroborating_signals += 1

    return 2 if corroborating_signals >= 2 else 1


def _derive_repair_scope(*, blocker_family: str, attempt_index: int, evidence_tier: int) -> str:
    if blocker_family not in SELF_HEALABLE_BLOCKER_FAMILIES:
        return "none"
    if attempt_index <= 1:
        return "local_runtime_repair"
    if evidence_tier >= 2:
        return "global_runtime_policy_repair"
    return "local_runtime_repair"


def _count_attempts_for_family(summaries: list[dict[str, Any]], blocker_family: str) -> int:
    return sum(1 for summary in summaries if summary.get("blocker_family") == blocker_family)


def _last_blocker_status_for_family(summaries: list[dict[str, Any]], blocker_family: str) -> str | None:
    for summary in reversed(summaries):
        if summary.get("blocker_family") == blocker_family:
            return summary.get("last_blocker_status")
    return None


def _normalize_stop_class(
    *,
    blocker_family: str,
    attempt_index: int,
    repair_budget_remaining: int,
    last_blocker_status: str | None,
    verifier_result: dict[str, Any],
) -> str:
    blocker_status = str(verifier_result.get("blocker_status") or "")
    next_safe_action = str(verifier_result.get("next_safe_action") or "stop")
    human_review_required = bool(verifier_result.get("human_review_required"))
    result_class = str(verifier_result.get("result_class") or "")

    if blocker_status == "semantic_boundary_touched" or result_class == "semantic_ambiguity_reached":
        return "semantic_boundary_touched"
    if human_review_required or next_safe_action == "human_review":
        return "human_review_required"
    if blocker_status in {"moved", "cleared"} and next_safe_action == "continue":
        return "completed_slice_continue_allowed"
    if blocker_family in SELF_HEALABLE_BLOCKER_FAMILIES and blocker_status == "unchanged":
        if last_blocker_status == "unchanged" and attempt_index >= 2:
            return "runtime_blocker_stalled"
        if repair_budget_remaining <= 0:
            return "runtime_budget_exhausted"
        return "runtime_blocker_unchanged"
    if next_safe_action == "continue":
        return "completed_slice_continue_allowed"
    return "generic_stop"


def _make_run_summary(
    *,
    run_id: str,
    slice_id: str,
    run_profile_id: str,
    planner_result: dict[str, Any],
    worker_result: dict[str, Any],
    verifier_result: dict[str, Any],
    blocker_family: str,
    evidence_tier: int,
    attempt_index: int,
    repair_scope: str,
    repair_budget_remaining: int,
    last_blocker_status: str | None,
    stop_class: str,
) -> dict[str, Any]:
    blocker = planner_result.get("first_blocker") or worker_result.get("blocker_found") or {}
    blocker_status = str(verifier_result.get("blocker_status") or "not_evaluable")
    tests_run = list(verifier_result.get("tests_run") or [])
    evidence_artifacts = list(verifier_result.get("artifact_paths") or [])

    return {
        "run_id": run_id,
        "slice_id": slice_id,
        "run_profile_id": run_profile_id,
        "targeted_blocker": blocker,
        "blocker_family": blocker_family,
        "evidence_tier": evidence_tier,
        "attempt_index": attempt_index,
        "repair_scope": repair_scope,
        "repairs_attempted": attempt_index,
        "repair_budget_remaining": repair_budget_remaining,
        "last_blocker_status": blocker_status,
        "previous_blocker_status": last_blocker_status,
        "blocker_moved": blocker_status in {"moved", "cleared"},
        "stop_class": stop_class,
        "another_unattended_attempt_allowed": stop_class in {"completed_slice_continue_allowed", "runtime_blocker_unchanged"},
        "tests_run": tests_run,
        "artifacts": evidence_artifacts,
        "evidence_basis": list(worker_result.get("evidence_basis") or evidence_artifacts),
    }


def _apply_canonical_lane_bundle_to_planner_result(
    planner_result: dict[str, Any],
    *,
    blocker_family: str,
    repair_scope: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    lane_bundle = _canonical_lane_bundle(blocker_family=blocker_family, repair_scope=repair_scope)
    if lane_bundle is None:
        return planner_result, None

    normalized = dict(planner_result)
    normalized["verification_commands"] = list(lane_bundle["verification_commands"])
    normalized["in_scope_files"] = _merge_unique_items(
        lane_bundle["in_scope_files"],
        list(planner_result.get("in_scope_files") or []),
    )
    normalized["out_of_scope"] = _merge_unique_items(
        list(planner_result.get("out_of_scope") or []),
        lane_bundle["forbidden_changes"],
    )
    return normalized, lane_bundle


def _make_checkpoint(
    *,
    run_id: str,
    slice_id: str,
    workspace: Path,
    planner_result: dict[str, Any],
    evaluator_result: dict[str, Any],
    worker_result: dict[str, Any],
    verifier_result: dict[str, Any],
    preflight: dict[str, Any],
    output_paths: dict[str, str],
) -> dict[str, Any]:
    git_head = _git_run(workspace, "rev-parse", "HEAD")
    head_sha = git_head.stdout.strip() if git_head.returncode == 0 else None
    checkpoint = {
        "checkpoint_id": f"{run_id}:{slice_id}",
        "phase": "B-1",
        "task_id": slice_id,
        "git_base_sha": head_sha,
        "git_head_sha": head_sha,
        "files_changed": worker_result.get("files_changed", []),
        "tests_run": verifier_result.get("tests_run", []),
        "artifacts": list(output_paths.values()),
        "decision_log": [
            {
                "repo_truth_used": planner_result["repo_truth_refs"][0],
                "external_references_used": planner_result.get("external_refs_checked", []),
                "adopted_guidance": evaluator_result.get("approval_rationale", evaluator_result.get("architecture_rationale", "")),
                "rejected_guidance": None,
            }
        ],
        "rollback_plan": [
            {"step": "Inspect dirty-tree snapshots and current diff before any manual revert."}
        ],
        "revert_unit": {
            "type": "diff_snapshot",
            "safe_revert_command": None,
            "affected_runtime_behavior": False,
        },
        "next_safe_action": verifier_result.get("next_safe_action", "stop"),
        "next_unattended_action_allowed": verifier_result.get("next_safe_action", "stop") == "continue"
        and not bool(evaluator_result.get("human_review_required") or verifier_result.get("human_review_required")),
        "stop_conditions_checked": planner_result.get("stop_conditions", []),
        "architecture_debt_delta": list((evaluator_result.get("attack_findings") or {}).get("cleanup_debt") or []),
        "conditions": evaluator_result.get("conditions", []),
        "human_review_required": bool(
            evaluator_result.get("human_review_required") or verifier_result.get("human_review_required")
        ),
        "architecture_boundary_touched": evaluator_result.get("architecture_boundary_touched", []),
        "preflight_action": preflight.get("action"),
    }
    validate_role_output("checkpoint", checkpoint)
    return checkpoint


def _finalize_round_after_verifier(
    *,
    run_id: str,
    run_profile_id: str,
    slice_id: str,
    workspace: Path,
    planner_result: dict[str, Any],
    evaluator_result: dict[str, Any],
    worker_result: dict[str, Any],
    verifier_result: dict[str, Any],
    preflight: dict[str, Any],
    output_paths: dict[str, str],
    checkpoints_dir: Path,
    summaries_dir: Path,
    existing_summaries: list[dict[str, Any]],
    max_autonomous_repair_attempts_per_family: int,
) -> dict[str, Any]:
    missing_conditions: list[str] = []
    evaluator_conditions = list(evaluator_result.get("conditions") or [])
    if evaluator_conditions:
        verified = set(verifier_result.get("conditions_verified") or [])
        missing_conditions = [condition for condition in evaluator_conditions if condition not in verified]

    derived_blocker_family = _classify_blocker_family(
        planner_result,
        worker_result,
        verifier_result,
    )
    blocker_family = _normalize_blocker_family_name(
        worker_result.get("blocker_family") or verifier_result.get("blocker_family") or derived_blocker_family
    )
    attempt_index = _count_attempts_for_family(existing_summaries, blocker_family) + 1
    derived_evidence_tier = _derive_evidence_tier(
        attempt_index=attempt_index,
        planner_result=planner_result,
        worker_result=worker_result,
        verifier_result=verifier_result,
    )
    verifier_evidence_tier = verifier_result.get("evidence_tier")
    evidence_tier = max(
        int(verifier_evidence_tier) if verifier_evidence_tier is not None else 0,
        derived_evidence_tier,
    )
    repair_scope = worker_result.get("repair_scope") or _derive_repair_scope(
        blocker_family=blocker_family,
        attempt_index=attempt_index,
        evidence_tier=evidence_tier,
    )
    last_blocker_status = _last_blocker_status_for_family(existing_summaries, blocker_family)
    repair_budget_remaining = max(0, max_autonomous_repair_attempts_per_family - attempt_index)
    stop_class = str(
        verifier_result.get("stop_class")
        or _normalize_stop_class(
            blocker_family=blocker_family,
            attempt_index=attempt_index,
            repair_budget_remaining=repair_budget_remaining,
            last_blocker_status=last_blocker_status,
            verifier_result=verifier_result,
        )
    )

    checkpoint = _make_checkpoint(
        run_id=run_id,
        slice_id=slice_id,
        workspace=workspace,
        planner_result=planner_result,
        evaluator_result=evaluator_result,
        worker_result=worker_result,
        verifier_result=verifier_result,
        preflight=preflight,
        output_paths=output_paths,
    )
    checkpoint_path = checkpoints_dir / f"{slice_id}.json"
    _json_dump(checkpoint_path, checkpoint)
    summary = _make_run_summary(
        run_id=run_id,
        slice_id=slice_id,
        run_profile_id=run_profile_id,
        planner_result=planner_result,
        worker_result=worker_result,
        verifier_result=verifier_result,
        blocker_family=blocker_family,
        evidence_tier=evidence_tier,
        attempt_index=attempt_index,
        repair_scope=repair_scope,
        repair_budget_remaining=repair_budget_remaining,
        last_blocker_status=last_blocker_status,
        stop_class=stop_class,
    )
    summary_path = summaries_dir / f"{slice_id}.json"
    _json_dump(summary_path, summary)
    _json_dump(summaries_dir / "latest_summary.json", summary)

    if missing_conditions and checkpoint["next_safe_action"] == "continue" and not checkpoint["human_review_required"]:
        return {
            "status": "blocked",
            "stop_reason": "verifier_conditions_not_verified",
            "run_dir": str(checkpoints_dir.parent),
            "missing_conditions": missing_conditions,
        }

    if stop_class == "human_review_required" or checkpoint["human_review_required"]:
        return {
            "status": "stopped",
            "stop_reason": "human_review_required",
            "run_dir": str(checkpoints_dir.parent),
        }

    next_safe_action = checkpoint["next_safe_action"]
    if stop_class != "completed_slice_continue_allowed" and next_safe_action != "continue":
        return {
            "status": "stopped",
            "stop_reason": stop_class if stop_class in STOP_CLASS_VALUES else next_safe_action,
            "run_dir": str(checkpoints_dir.parent),
        }

    return {
        "status": "continue",
        "checkpoint_path": str(checkpoint_path),
        "summary_path": str(summary_path),
        "stop_class": stop_class,
    }


def run_autorun(
    *,
    workspace: Path,
    run_root: Path,
    role_execution_mode: str,
    dirty_policy: str,
    max_slices: int | None,
    role_timeout_seconds: int | None,
    role_timeout_overrides: dict[str, int] | None = None,
    mock_scenario_path: Path | None = None,
    run_id: str | None = None,
    resume_run_id: str | None = None,
    run_profile_id: str | None = None,
) -> dict[str, Any]:
    run_profile = _get_run_profile(run_profile_id)
    resolved_run_id = resume_run_id or run_id or f"b1-dry-run-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = run_root / "runs" / resolved_run_id
    prompts_dir = run_dir / "prompts"
    outputs_dir = run_dir / "outputs"
    checkpoints_dir = run_dir / "checkpoints"
    summaries_dir = run_dir / "summaries"
    preflight_dir = run_dir / "preflight"
    run_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    resolved_max_slices = max_slices if max_slices is not None else int(run_profile["max_slices"])

    truth = _load_latest_truth()
    if resume_run_id:
        resume_state = _read_existing_run_state(run_dir=run_dir)
        manifest = dict(resume_state["manifest"])
        manifest["role_execution_mode"] = role_execution_mode
        manifest["dirty_policy"] = dirty_policy
        manifest["max_slices"] = resolved_max_slices
        manifest["role_timeout_seconds"] = role_timeout_seconds
        manifest["role_timeout_overrides"] = role_timeout_overrides or {}
        manifest["default_role_timeout_seconds_by_role"] = DEFAULT_ROLE_TIMEOUT_SECONDS_BY_ROLE
        manifest["run_profile_id"] = run_profile["run_profile_id"]
        manifest["run_profile"] = run_profile
        manifest["latest_readiness_path"] = truth["latest_readiness_path"]
        manifest["latest_full_smoke_path"] = truth["latest_full_smoke_path"]
        manifest["resume_count"] = int(manifest.get("resume_count", 0)) + 1
        manifest["last_resumed_at_utc"] = _utc_now()
        manifest["last_resume_state"] = {
            "round_index": resume_state["round_index"],
            "next_role": resume_state["next_role"],
            "slice_id": resume_state["slice_id"],
            "checkpoint_pending": bool(resume_state["checkpoint_pending"]),
        }
        ledger: dict[str, Any] = dict(resume_state["ledger"])
    else:
        resume_state = None
        manifest = {
            "run_id": resolved_run_id,
            "phase": "B-1",
            "slice_mode": "dry_run_only",
            "run_profile_id": run_profile["run_profile_id"],
            "run_profile": run_profile,
            "role_execution_mode": role_execution_mode,
            "dirty_policy": dirty_policy,
            "max_slices": resolved_max_slices,
            "role_timeout_seconds": role_timeout_seconds,
            "role_timeout_overrides": role_timeout_overrides or {},
            "default_role_timeout_seconds_by_role": DEFAULT_ROLE_TIMEOUT_SECONDS_BY_ROLE,
            "workspace": str(workspace),
            "prompt_template_dir": str(PROMPT_TEMPLATE_DIR),
            "schema_dir": str(SCHEMA_DIR),
            "next_live_target": DEFAULT_NEXT_LIVE_TARGET,
            "latest_readiness_path": truth["latest_readiness_path"],
            "latest_full_smoke_path": truth["latest_full_smoke_path"],
            "started_at_utc": _utc_now(),
        }
        ledger = {"run_id": resolved_run_id, "events": []}
    _json_dump(run_dir / "manifest.json", manifest)

    mock_scenario = _json_load(mock_scenario_path) if mock_scenario_path else None

    preflight = perform_preflight(workspace=workspace, preflight_dir=preflight_dir, dirty_policy=dirty_policy)
    ledger["events"].append(
        {
            "role": "preflight",
            "status": preflight["action"],
            "artifact": str(preflight_dir / "dirty_tree_report.json"),
            "timestamp_utc": _utc_now(),
        }
    )
    _json_dump(run_dir / "ledger.json", ledger)

    if preflight["action"] == "stop":
        return {
            "status": "blocked",
            "stop_reason": "dirty_tree_stop",
            "run_dir": str(run_dir),
        }

    if resume_state is not None:
        ledger["events"].append(
            {
                "role": "resume",
                "status": "continue",
                "artifact": str(run_dir / "manifest.json"),
                "timestamp_utc": _utc_now(),
                "round_index": resume_state["round_index"],
                "next_role": resume_state["next_role"],
                "slice_id": resume_state["slice_id"],
                "checkpoint_pending": bool(resume_state["checkpoint_pending"]),
            }
        )
        _json_dump(run_dir / "ledger.json", ledger)

    round_index = int(resume_state["round_index"]) if resume_state is not None else 0
    final_result = {"status": "stopped", "stop_reason": "max_slices_reached", "run_dir": str(run_dir)}
    while round_index < resolved_max_slices:
        if resume_state is not None and round_index == int(resume_state["round_index"]):
            slice_id = resume_state["slice_id"] or f"B1-dry-run-{round_index + 1:03d}"
            previous_artifact_path = resume_state["previous_artifact_path"]
            role_outputs = dict(resume_state["role_outputs"])
            output_paths = dict(resume_state["output_paths"])
            planner_scope = dict(resume_state["planner_scope"])
            narrowed_boundary = str(resume_state["narrowed_boundary"])
            evaluator_conditions = list(resume_state["evaluator_conditions"])
            if resume_state["checkpoint_pending"]:
                roles_to_run = ()
            else:
                start_role_index = ROLE_ORDER.index(str(resume_state["next_role"]))
                roles_to_run = ROLE_ORDER[start_role_index:]
        else:
            slice_id = f"B1-dry-run-{round_index + 1:03d}"
            previous_artifact_path = None
            role_outputs = {}
            output_paths = {}
            planner_scope = {
                "in_scope_files": [],
                "verification_commands": [],
                "stop_conditions": [],
                "out_of_scope": [],
            }
            narrowed_boundary = ""
            evaluator_conditions = []
            roles_to_run = ROLE_ORDER

        existing_summaries = _load_existing_summaries(summaries_dir)
        current_blocker_family = _normalize_blocker_family_name(_classify_blocker_family(role_outputs.get("planner")))
        current_attempt_index = _count_attempts_for_family(existing_summaries, current_blocker_family) + 1
        current_evidence_tier = _derive_evidence_tier(
            attempt_index=current_attempt_index,
            planner_result=role_outputs.get("planner", {}),
            worker_result=role_outputs.get("worker", {}),
            verifier_result=role_outputs.get("verifier", {}),
        )
        current_repair_scope = _derive_repair_scope(
            blocker_family=current_blocker_family,
            attempt_index=current_attempt_index,
            evidence_tier=current_evidence_tier,
        )
        current_lane_bundle = _canonical_lane_bundle(
            blocker_family=current_blocker_family,
            repair_scope=current_repair_scope,
        )
        current_last_blocker_status = _last_blocker_status_for_family(existing_summaries, current_blocker_family)
        current_repair_budget_remaining = max(
            0,
            int(run_profile["max_autonomous_repair_attempts_per_family"]) - current_attempt_index,
        )

        if (
            resume_state is not None
            and round_index == int(resume_state["round_index"])
            and resume_state["checkpoint_pending"]
        ):
            existing_summaries = _load_existing_summaries(summaries_dir)
            finalize_result = _finalize_round_after_verifier(
                run_id=resolved_run_id,
                run_profile_id=run_profile["run_profile_id"],
                slice_id=slice_id,
                workspace=workspace,
                planner_result=role_outputs["planner"],
                evaluator_result=role_outputs["evaluator"],
                worker_result=role_outputs["worker"],
                verifier_result=role_outputs["verifier"],
                preflight=preflight,
                output_paths=output_paths,
                checkpoints_dir=checkpoints_dir,
                summaries_dir=summaries_dir,
                existing_summaries=existing_summaries,
                max_autonomous_repair_attempts_per_family=int(run_profile["max_autonomous_repair_attempts_per_family"]),
            )
            if finalize_result["status"] != "continue":
                return finalize_result
            output_paths["checkpoint"] = str(checkpoints_dir / f"{slice_id}.json")
            previous_artifact_path = output_paths["checkpoint"]
            round_index += 1
            resume_state = None
            continue

        for role in roles_to_run:
            role_context = {
                "run_id": resolved_run_id,
                "run_profile_id": run_profile["run_profile_id"],
                "slice_id": slice_id,
                "latest_readiness_path": truth["latest_readiness_path"],
                "latest_full_smoke_path": truth["latest_full_smoke_path"],
                "previous_role_artifact_path": previous_artifact_path,
                "in_scope_files": planner_scope["in_scope_files"],
                "forbidden_changes": planner_scope["out_of_scope"],
                "verification_commands": planner_scope["verification_commands"],
                "stop_conditions": planner_scope["stop_conditions"],
                "narrowed_boundary": narrowed_boundary,
                "conditions": evaluator_conditions,
                "next_live_target": DEFAULT_NEXT_LIVE_TARGET,
                "attempt_index": current_attempt_index,
                "blocker_family": current_blocker_family,
                "evidence_tier": current_evidence_tier,
                "repair_scope": current_repair_scope,
                "repair_budget_remaining": current_repair_budget_remaining,
                "last_blocker_status": current_last_blocker_status,
                "max_autonomous_repair_attempts_per_family": run_profile["max_autonomous_repair_attempts_per_family"],
                "repair_lane_id": (current_lane_bundle or {}).get("repair_lane_id"),
                "canonical_verification_bundle": (current_lane_bundle or {}).get("verification_commands", []),
                "runtime_repair_in_scope_files": (current_lane_bundle or {}).get("in_scope_files", []),
                "runtime_repair_forbidden_changes": (current_lane_bundle or {}).get("forbidden_changes", []),
            }
            prompt_text = _render_prompt_snapshot(role, context=role_context)
            prompt_path = _write_prompt_snapshot(prompts_dir, round_index=round_index, role=role, prompt_text=prompt_text)

            if role_execution_mode == "mock":
                assert mock_scenario is not None
                payload = _load_mock_role_output(mock_scenario, round_index=round_index, role=role)
            elif role_execution_mode == "live_cli":
                if role == "worker":
                    profile_timeout_default = int(
                        run_profile["worker_timeout_seconds"]["provider_runtime_repair_slice"]
                        if current_repair_scope in {"local_runtime_repair", "global_runtime_policy_repair"}
                        else run_profile["worker_timeout_seconds"]["ordinary_implementation_slice"]
                    )
                elif role in {"planner", "evaluator", "verifier"}:
                    profile_timeout_default = int(run_profile[f"{role}_timeout_seconds"])
                else:
                    profile_timeout_default = DEFAULT_ROLE_TIMEOUT_SECONDS_BY_ROLE[role]
                current_role_timeout_seconds = (
                    (role_timeout_overrides or {}).get(role)
                    or role_timeout_seconds
                    or profile_timeout_default
                )
                try:
                    payload = invoke_live_cli_role(
                        role=role,
                        prompt_path=prompt_path,
                        workspace=workspace,
                        timeout_seconds=current_role_timeout_seconds,
                    )
                except RoleExecutionTimeoutError as exc:
                    ledger["events"].append(
                        {
                            "role": role,
                            "status": "timed_out",
                            "input_prompt_file": str(prompt_path),
                            "output_artifact": None,
                            "started_at_utc": _utc_now(),
                            "ended_at_utc": _utc_now(),
                            "next_action": "stop",
                            "error": str(exc),
                        }
                    )
                    _json_dump(run_dir / "ledger.json", ledger)
                    return {
                        "status": "blocked",
                        "stop_reason": "role_timeout",
                        "run_dir": str(run_dir),
                        "role": role,
                        "error": str(exc),
                    }
            else:
                payload = _default_noop_role_output(
                    role,
                    run_id=resolved_run_id,
                    slice_id=slice_id,
                    current_full_smoke=truth["latest_full_smoke_path"],
                )

            try:
                validated = validate_role_output(role, payload)
            except RoleOutputValidationError as exc:
                ledger["events"].append(
                    {
                        "role": role,
                        "status": "blocked",
                        "input_prompt_file": str(prompt_path),
                        "output_artifact": None,
                        "started_at_utc": _utc_now(),
                        "ended_at_utc": _utc_now(),
                        "next_action": "stop",
                        "error": str(exc),
                    }
                )
                _json_dump(run_dir / "ledger.json", ledger)
                return {
                    "status": "blocked",
                    "stop_reason": "malformed_role_output",
                    "run_dir": str(run_dir),
                    "role": role,
                    "error": str(exc),
                }
            output_path = _write_role_output(outputs_dir, round_index=round_index, role=role, payload=validated)
            role_outputs[role] = validated
            output_paths[role] = str(output_path)
            previous_artifact_path = str(output_path)

            ledger["events"].append(
                {
                    "role": role,
                    "status": validated.get("verdict", validated.get("status", validated.get("result_class", "completed"))),
                    "input_prompt_file": str(prompt_path),
                    "output_artifact": str(output_path),
                    "started_at_utc": _utc_now(),
                    "ended_at_utc": _utc_now(),
                    "next_action": None,
                }
            )
            _json_dump(run_dir / "ledger.json", ledger)

            if role == "planner":
                planner_blocker_family = _normalize_blocker_family_name(_classify_blocker_family(validated))
                planner_attempt_index = _count_attempts_for_family(existing_summaries, planner_blocker_family) + 1
                planner_evidence_tier = _derive_evidence_tier(
                    attempt_index=planner_attempt_index,
                    planner_result=validated,
                    worker_result=role_outputs.get("worker", {}),
                    verifier_result=role_outputs.get("verifier", {}),
                )
                planner_repair_scope = _derive_repair_scope(
                    blocker_family=planner_blocker_family,
                    attempt_index=planner_attempt_index,
                    evidence_tier=planner_evidence_tier,
                )
                normalized_planner_result, normalized_lane_bundle = _apply_canonical_lane_bundle_to_planner_result(
                    validated,
                    blocker_family=planner_blocker_family,
                    repair_scope=planner_repair_scope,
                )
                if normalized_planner_result is not validated:
                    validated = normalized_planner_result
                    role_outputs[role] = validated
                    _write_role_output(outputs_dir, round_index=round_index, role=role, payload=validated)
                    output_paths[role] = str(outputs_dir / f"{round_index:02d}_{role}.json")
                    previous_artifact_path = output_paths[role]
                planner_scope = {
                    "in_scope_files": validated.get("in_scope_files", []),
                    "verification_commands": validated.get("verification_commands", []),
                    "stop_conditions": validated.get("stop_conditions", []),
                    "out_of_scope": validated.get("out_of_scope", []),
                }
                slice_id = validated["slice_id"]
                current_blocker_family = planner_blocker_family
                current_attempt_index = planner_attempt_index
                current_evidence_tier = planner_evidence_tier
                current_repair_scope = planner_repair_scope
                current_lane_bundle = normalized_lane_bundle or _canonical_lane_bundle(
                    blocker_family=current_blocker_family,
                    repair_scope=current_repair_scope,
                )
                current_last_blocker_status = _last_blocker_status_for_family(existing_summaries, current_blocker_family)
                current_repair_budget_remaining = max(
                    0,
                    int(run_profile["max_autonomous_repair_attempts_per_family"]) - current_attempt_index,
                )

            if role == "evaluator":
                narrowed_boundary = validated.get("narrowed_boundary") or ""
                evaluator_conditions = list(validated.get("conditions") or [])
                verdict = validated["verdict"]
                if verdict == "reject":
                    final_result = {
                        "status": "stopped",
                        "stop_reason": "evaluator_reject",
                        "run_dir": str(run_dir),
                    }
                    return final_result

            if role == "verifier":
                finalize_result = _finalize_round_after_verifier(
                    run_id=resolved_run_id,
                    run_profile_id=run_profile["run_profile_id"],
                    slice_id=slice_id,
                    workspace=workspace,
                    planner_result=role_outputs["planner"],
                    evaluator_result=role_outputs["evaluator"],
                    worker_result=role_outputs["worker"],
                    verifier_result=role_outputs["verifier"],
                    preflight=preflight,
                    output_paths=output_paths,
                    checkpoints_dir=checkpoints_dir,
                    summaries_dir=summaries_dir,
                    existing_summaries=existing_summaries,
                    max_autonomous_repair_attempts_per_family=int(run_profile["max_autonomous_repair_attempts_per_family"]),
                )
                output_paths["checkpoint"] = str(checkpoints_dir / f"{slice_id}.json")
                previous_artifact_path = output_paths["checkpoint"]
                if finalize_result["status"] != "continue":
                    return finalize_result

        round_index += 1
        if resume_state is not None and round_index > int(resume_state["round_index"]):
            resume_state = None

    return final_result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=str(ROOT))
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--run-profile", default=DEFAULT_RUN_PROFILE_ID)
    parser.add_argument("--role-execution-mode", choices=["mock", "noop_cli", "live_cli"], default="noop_cli")
    parser.add_argument("--mock-scenario-path")
    parser.add_argument("--dirty-policy", choices=["stop", "snapshot"], default="stop")
    parser.add_argument("--max-slices", type=int, default=None)
    parser.add_argument("--role-timeout-seconds", type=int, default=None)
    parser.add_argument("--planner-timeout-seconds", type=int, default=None)
    parser.add_argument("--evaluator-timeout-seconds", type=int, default=None)
    parser.add_argument("--worker-timeout-seconds", type=int, default=None)
    parser.add_argument("--verifier-timeout-seconds", type=int, default=None)
    parser.add_argument("--run-id")
    parser.add_argument("--resume-run-id")
    args = parser.parse_args(argv)
    role_timeout_overrides = _build_role_timeout_overrides_from_args(args)

    result = run_autorun(
        workspace=Path(args.workspace),
        run_root=Path(args.run_root),
        role_execution_mode=args.role_execution_mode,
        dirty_policy=args.dirty_policy,
        max_slices=args.max_slices,
        role_timeout_seconds=args.role_timeout_seconds,
        role_timeout_overrides=role_timeout_overrides or None,
        mock_scenario_path=Path(args.mock_scenario_path) if args.mock_scenario_path else None,
        run_id=args.run_id,
        resume_run_id=args.resume_run_id,
        run_profile_id=args.run_profile,
    )
    sys_out = json.dumps(result, ensure_ascii=False, indent=2)
    print(sys_out)
    return 0 if result["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
