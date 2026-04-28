from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import run_b1_cli_autorun


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True, text=True)
    tracked = path / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


def _write_mock_scenario(path: Path, scenario: dict) -> Path:
    scenario_path = path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
    return scenario_path


def test_preflight_snapshot_writes_status_and_diff_when_dirty(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)
    (workspace / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (workspace / "note.txt").write_text("untracked\n", encoding="utf-8")

    run_dir = tmp_path / "run"
    run_dir.mkdir()

    preflight = run_b1_cli_autorun.perform_preflight(
        workspace=workspace,
        preflight_dir=run_dir / "preflight",
        dirty_policy="snapshot",
    )

    assert preflight["dirty"] is True
    assert preflight["action"] == "snapshot"
    assert (run_dir / "preflight" / "git_status.txt").exists()
    assert (run_dir / "preflight" / "git_diff.patch").exists()
    assert (run_dir / "preflight" / "dirty_tree_report.json").exists()


def test_coordinator_stops_before_worker_when_evaluator_rejects(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-1",
                    "slice_id": "B1-dry-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://platform.openai.com/docs/guides/evaluation-best-practices"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required", "ready_for_phase_b1_implementation"],
                },
                "evaluator": {
                    "verdict": "reject",
                    "architecture_rationale": "Would broaden scope too early.",
                    "ux_journey_rationale": "No need to touch runtime yet.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": ["scope creep"],
                        "approve_condition": [],
                        "cleanup_debt": [],
                    },
                    "conditions": [],
                    "approval_rationale": "Reject because this would broaden runtime scope too early.",
                    "checked_context_packs": [
                        "UX / Product Journey",
                        "Product Semantics",
                        "Architecture Transition",
                        "Current Repo Truth",
                    ],
                    "architecture_boundary_touched": ["eval_only"],
                },
            }
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=4,
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "evaluator_reject"

    ledger = json.loads((Path(result["run_dir"]) / "ledger.json").read_text(encoding="utf-8"))
    roles = [
        entry["role"]
        for entry in ledger["events"]
        if entry.get("role") in {"planner", "evaluator", "worker", "verifier"}
    ]
    assert roles == ["planner", "evaluator"]


def test_coordinator_propagates_narrowed_boundary_and_writes_checkpoint(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-2",
                    "slice_id": "B1-dry-002",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py", "tests/test_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required", "ready_for_phase_b1_implementation"],
                },
                "evaluator": {
                    "verdict": "approve_with_narrower_boundary",
                    "architecture_rationale": "Keep this dry-run only.",
                    "ux_journey_rationale": "Preserves chat-first boundary.",
                    "narrowed_boundary": "Only dry-run coordinator flow and artifacts; no live runtime edits.",
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": [],
                        "cleanup_debt": ["keep B-1 live runtime untouched"],
                    },
                    "conditions": [],
                    "approval_rationale": "Approve with narrower boundary because the slice is infrastructure-only.",
                    "checked_context_packs": [
                        "UX / Product Journey",
                        "Product Semantics",
                        "Architecture Transition",
                        "Current Repo Truth",
                    ],
                    "architecture_boundary_touched": ["eval_only"],
                },
                "worker": {
                    "status": "completed",
                    "files_changed": [],
                    "commands_run": ["python scripts/run_b1_cli_autorun.py --execution-mode noop_cli"],
                    "blocker_found": None,
                    "conditions_followed": [],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Dry-run only.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [
                        {"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}
                    ],
                    "artifact_paths": [],
                    "readiness_delta": "none",
                    "conditions_verified": [],
                    "blocker_status": "not_evaluable",
                    "next_safe_action": "stop",
                    "human_review_required": False,
                },
            }
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=4,
    )

    run_dir = Path(result["run_dir"])
    worker_prompt = next((run_dir / "prompts").glob("*worker*.md")).read_text(encoding="utf-8")
    assert "Only dry-run coordinator flow and artifacts; no live runtime edits." in worker_prompt

    checkpoint_path = next((run_dir / "checkpoints").glob("*.json"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["revert_unit"]["type"] == "diff_snapshot"
    assert checkpoint["revert_unit"]["affected_runtime_behavior"] is False
    assert checkpoint["human_review_required"] is False
    assert checkpoint["next_unattended_action_allowed"] is False
    assert checkpoint["architecture_debt_delta"] == ["keep B-1 live runtime untouched"]


def test_coordinator_propagates_conditions_and_cleanup_debt_without_blocking(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-3",
                    "slice_id": "B1-dry-003",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": [],
                    "external_research_required": False,
                    "external_research_omitted_reason": "Repo-local dry-run contract is sufficient for this governance-only slice.",
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py", "docs/agent/autonomy-prompts/"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required", "ready_for_phase_b1_implementation"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Proceed only if this remains dry-run and checkpointed.",
                    "ux_journey_rationale": "No live behavior changes; conditions preserve low-friction logging semantics.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": [
                            "Keep the slice dry-run only.",
                            "Do not modify live B-1 runtime behavior.",
                        ],
                        "cleanup_debt": ["Prompt assets may still need future compression."],
                    },
                    "conditions": [
                        "Keep the slice dry-run only.",
                        "Do not modify live B-1 runtime behavior.",
                    ],
                    "approval_rationale": "The slice is directionally correct if the dry-run guardrails are enforced.",
                    "checked_context_packs": [
                        "UX / Product Journey",
                        "Product Semantics",
                        "Architecture Transition",
                        "Current Repo Truth",
                    ],
                    "architecture_boundary_touched": ["eval_only"],
                },
                "worker": {
                    "status": "completed",
                    "files_changed": [],
                    "commands_run": ["python scripts/run_b1_cli_autorun.py --role-execution-mode noop_cli"],
                    "blocker_found": None,
                    "conditions_followed": [
                        "Keep the slice dry-run only.",
                        "Do not modify live B-1 runtime behavior.",
                    ],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Dry-run scaffolding only; evaluator conditions preserved.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [
                        {"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}
                    ],
                    "artifact_paths": [],
                    "readiness_delta": "none",
                    "conditions_verified": [
                        "Keep the slice dry-run only.",
                        "Do not modify live B-1 runtime behavior.",
                    ],
                    "blocker_status": "unchanged",
                    "next_safe_action": "stop",
                    "human_review_required": False,
                },
            }
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=4,
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "stop"

    run_dir = Path(result["run_dir"])
    worker_prompt = next((run_dir / "prompts").glob("*worker*.md")).read_text(encoding="utf-8")
    verifier_prompt = next((run_dir / "prompts").glob("*verifier*.md")).read_text(encoding="utf-8")
    assert "Keep the slice dry-run only." in worker_prompt
    assert "Do not modify live B-1 runtime behavior." in verifier_prompt

    checkpoint_path = next((run_dir / "checkpoints").glob("*.json"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["conditions"] == [
        "Keep the slice dry-run only.",
        "Do not modify live B-1 runtime behavior.",
    ]
    assert checkpoint["architecture_debt_delta"] == ["Prompt assets may still need future compression."]
    assert checkpoint["next_unattended_action_allowed"] is False


def test_malformed_evaluator_output_blocks_run(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-4",
                    "slice_id": "B1-dry-004",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://platform.openai.com/docs/guides/evaluation-best-practices"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required", "ready_for_phase_b1_implementation"],
                },
                "evaluator": {
                    "verdict": "approve",
                    "architecture_rationale": "Malformed on purpose.",
                    "ux_journey_rationale": "Malformed on purpose.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "conditions": [],
                    "approval_rationale": "Malformed on purpose.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["eval_only"],
                },
            }
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=4,
    )

    assert result["status"] == "blocked"
    assert result["stop_reason"] == "malformed_role_output"


def test_planner_requires_omission_reason_when_external_refs_are_empty() -> None:
    payload = {
        "run_id": "run-5",
        "slice_id": "B1-dry-005",
        "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
        "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
        "external_refs_checked": [],
        "external_research_required": False,
        "external_research_omitted_reason": "",
        "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
        "out_of_scope": ["app/runtime/**"],
        "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
        "stop_conditions": ["human_review_required"],
    }

    with pytest.raises(run_b1_cli_autorun.RoleOutputValidationError):
        run_b1_cli_autorun.validate_role_output("planner", payload)


def test_worker_requires_blocked_status_when_blocker_found() -> None:
    payload = {
        "status": "completed",
        "files_changed": [],
        "commands_run": ["python scripts/run_b1_cli_autorun.py --role-execution-mode noop_cli"],
        "blocker_found": {"code": "adjacent_blocker", "detail": "new blocker surfaced"},
        "conditions_followed": [],
        "out_of_scope_changes_avoided": True,
        "notes": "Should not be allowed to complete while reporting a blocker.",
    }

    with pytest.raises(run_b1_cli_autorun.RoleOutputValidationError):
        run_b1_cli_autorun.validate_role_output("worker", payload)


def test_verifier_refuses_fixed_without_artifact_backed_blocker_movement() -> None:
    payload = {
        "result_class": "fixed",
        "tests_run": [
            {"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}
        ],
        "artifact_paths": [],
        "readiness_delta": "none",
        "conditions_verified": [],
        "blocker_status": "unchanged",
        "next_safe_action": "continue",
        "human_review_required": False,
    }

    with pytest.raises(run_b1_cli_autorun.RoleOutputValidationError):
        run_b1_cli_autorun.validate_role_output("verifier", payload)


def test_prompt_templates_and_schema_assets_exist() -> None:
    root = Path(run_b1_cli_autorun.ROOT)

    prompt_dir = root / "docs" / "agent" / "autonomy-prompts"
    schema_dir = root / "docs" / "agent" / "autonomy-schemas"

    assert (prompt_dir / "B1_PLANNER_PROMPT.md").exists()
    assert (prompt_dir / "B1_EVALUATOR_PROMPT.md").exists()
    assert (prompt_dir / "B1_WORKER_PROMPT.md").exists()
    assert (prompt_dir / "B1_VERIFIER_PROMPT.md").exists()
    assert (schema_dir / "planner_result.schema.json").exists()
    assert (schema_dir / "evaluator_result.schema.json").exists()
    assert (schema_dir / "worker_result.schema.json").exists()
    assert (schema_dir / "verifier_result.schema.json").exists()
    assert (schema_dir / "checkpoint.schema.json").exists()

    evaluator_prompt = (prompt_dir / "B1_EVALUATOR_PROMPT.md").read_text(encoding="utf-8")
    assert "UX / Product Journey" in evaluator_prompt
    assert "approve_with_conditions" in evaluator_prompt
    assert "approve_with_narrower_boundary" in evaluator_prompt

    evaluator_schema = json.loads((schema_dir / "evaluator_result.schema.json").read_text(encoding="utf-8"))
    assert "verdict" in evaluator_schema["required"]
    assert "architecture_rationale" in evaluator_schema["required"]
