from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROMPT_TEMPLATE_DIR = ROOT / "docs" / "agent" / "autonomy-prompts"
SCHEMA_DIR = ROOT / "docs" / "agent" / "autonomy-schemas"
DEFAULT_RUN_ROOT = ROOT / "artifacts" / "recovery" / "b1_autorun"
DEFAULT_NEXT_LIVE_TARGET = "B1-004 real Pass 2 trace/provider contract completeness"
LATEST_READINESS_PATH = ROOT / "artifacts" / "wave1_phase_b_minimal_tool_loop_readiness.json"
LATEST_FULL_SMOKE_GLOB = "wave1_phase_b_minimal_tool_loop_smoke_*.json"

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


class RoleOutputValidationError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _latest_full_smoke_path() -> Path | None:
    matches = sorted((ROOT / "artifacts").glob(LATEST_FULL_SMOKE_GLOB), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


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


def _load_latest_truth() -> dict[str, Any]:
    return {
        "latest_readiness_path": str(LATEST_READINESS_PATH) if LATEST_READINESS_PATH.exists() else None,
        "latest_full_smoke_path": str(_latest_full_smoke_path()) if _latest_full_smoke_path() else None,
    }


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


def run_autorun(
    *,
    workspace: Path,
    run_root: Path,
    role_execution_mode: str,
    dirty_policy: str,
    max_slices: int,
    mock_scenario_path: Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    resolved_run_id = run_id or f"b1-dry-run-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = run_root / "runs" / resolved_run_id
    prompts_dir = run_dir / "prompts"
    outputs_dir = run_dir / "outputs"
    checkpoints_dir = run_dir / "checkpoints"
    preflight_dir = run_dir / "preflight"
    run_dir.mkdir(parents=True, exist_ok=True)

    truth = _load_latest_truth()
    manifest = {
        "run_id": resolved_run_id,
        "phase": "B-1",
        "slice_mode": "dry_run_only",
        "role_execution_mode": role_execution_mode,
        "dirty_policy": dirty_policy,
        "max_slices": max_slices,
        "workspace": str(workspace),
        "prompt_template_dir": str(PROMPT_TEMPLATE_DIR),
        "schema_dir": str(SCHEMA_DIR),
        "next_live_target": DEFAULT_NEXT_LIVE_TARGET,
        "latest_readiness_path": truth["latest_readiness_path"],
        "latest_full_smoke_path": truth["latest_full_smoke_path"],
        "started_at_utc": _utc_now(),
    }
    _json_dump(run_dir / "manifest.json", manifest)

    ledger: dict[str, Any] = {"run_id": resolved_run_id, "events": []}
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

    round_index = 0
    final_result = {"status": "stopped", "stop_reason": "max_slices_reached", "run_dir": str(run_dir)}
    while round_index < max_slices:
        slice_id = f"B1-dry-run-{round_index + 1:03d}"
        previous_artifact_path: str | None = None
        role_outputs: dict[str, dict[str, Any]] = {}
        output_paths: dict[str, str] = {}
        planner_scope: dict[str, Any] = {
            "in_scope_files": [],
            "verification_commands": [],
            "stop_conditions": [],
            "out_of_scope": [],
        }
        narrowed_boundary = ""
        evaluator_conditions: list[str] = []

        for role in ROLE_ORDER:
            role_context = {
                "run_id": resolved_run_id,
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
            }
            prompt_text = _render_prompt_snapshot(role, context=role_context)
            prompt_path = _write_prompt_snapshot(prompts_dir, round_index=round_index, role=role, prompt_text=prompt_text)

            if role_execution_mode == "mock":
                assert mock_scenario is not None
                payload = _load_mock_role_output(mock_scenario, round_index=round_index, role=role)
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
                planner_scope = {
                    "in_scope_files": validated.get("in_scope_files", []),
                    "verification_commands": validated.get("verification_commands", []),
                    "stop_conditions": validated.get("stop_conditions", []),
                    "out_of_scope": validated.get("out_of_scope", []),
                }
                slice_id = validated["slice_id"]

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

            if role == "worker" and evaluator_conditions:
                followed = set(validated.get("conditions_followed") or [])
                missing_conditions = [condition for condition in evaluator_conditions if condition not in followed]
                if missing_conditions:
                    return {
                        "status": "blocked",
                        "stop_reason": "worker_conditions_not_followed",
                        "run_dir": str(run_dir),
                        "missing_conditions": missing_conditions,
                    }

            if role == "verifier":
                if evaluator_conditions:
                    verified = set(validated.get("conditions_verified") or [])
                    missing_conditions = [condition for condition in evaluator_conditions if condition not in verified]
                    if missing_conditions:
                        return {
                            "status": "blocked",
                            "stop_reason": "verifier_conditions_not_verified",
                            "run_dir": str(run_dir),
                            "missing_conditions": missing_conditions,
                        }
                checkpoint = _make_checkpoint(
                    run_id=resolved_run_id,
                    slice_id=slice_id,
                    workspace=workspace,
                    planner_result=role_outputs["planner"],
                    evaluator_result=role_outputs["evaluator"],
                    worker_result=role_outputs["worker"],
                    verifier_result=role_outputs["verifier"],
                    preflight=preflight,
                    output_paths=output_paths,
                )
                checkpoint_path = checkpoints_dir / f"{slice_id}.json"
                _json_dump(checkpoint_path, checkpoint)
                output_paths["checkpoint"] = str(checkpoint_path)
                previous_artifact_path = str(checkpoint_path)

                if checkpoint["human_review_required"]:
                    return {
                        "status": "stopped",
                        "stop_reason": "human_review_required",
                        "run_dir": str(run_dir),
                    }

                next_safe_action = checkpoint["next_safe_action"]
                if next_safe_action != "continue":
                    return {
                        "status": "stopped",
                        "stop_reason": next_safe_action,
                        "run_dir": str(run_dir),
                    }

        round_index += 1

    return final_result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=str(ROOT))
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--role-execution-mode", choices=["mock", "noop_cli"], default="noop_cli")
    parser.add_argument("--mock-scenario-path")
    parser.add_argument("--dirty-policy", choices=["stop", "snapshot"], default="stop")
    parser.add_argument("--max-slices", type=int, default=1)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)

    result = run_autorun(
        workspace=Path(args.workspace),
        run_root=Path(args.run_root),
        role_execution_mode=args.role_execution_mode,
        dirty_policy=args.dirty_policy,
        max_slices=args.max_slices,
        mock_scenario_path=Path(args.mock_scenario_path) if args.mock_scenario_path else None,
        run_id=args.run_id,
    )
    sys_out = json.dumps(result, ensure_ascii=False, indent=2)
    print(sys_out)
    return 0 if result["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
