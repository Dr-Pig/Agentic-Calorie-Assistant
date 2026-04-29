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
        role_timeout_seconds=30,
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
                    "status": "blocked",
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
        role_timeout_seconds=30,
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
                    "status": "blocked",
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
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=4,
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "runtime_blocker_unchanged"

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


def test_worker_condition_omission_does_not_block_if_verifier_verifies_conditions(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-worker-omission",
                    "slice_id": "B1-dry-worker-omission",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": [],
                    "external_research_required": False,
                    "external_research_omitted_reason": "Mock dry-run scenario is repo-local only.",
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Proceed with explicit guardrails.",
                    "ux_journey_rationale": "No live product behavior changes.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": [
                            "Keep the slice dry-run only.",
                            "Do not modify live B-1 runtime behavior.",
                        ],
                        "cleanup_debt": [],
                    },
                    "conditions": [
                        "Keep the slice dry-run only.",
                        "Do not modify live B-1 runtime behavior.",
                    ],
                    "approval_rationale": "Bounded dry-run approval.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["eval_only"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python scripts/run_b1_cli_autorun.py --role-execution-mode noop_cli"],
                    "blocker_found": {"code": "upstream_blocker", "detail": "No live action taken."},
                    "conditions_followed": ["Keep the slice dry-run only."],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Stopped in bounds; omitted one echoed condition.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}],
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
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=1,
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "runtime_blocker_unchanged"


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
        role_timeout_seconds=30,
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


def test_extract_json_object_from_cli_output_reads_plain_json() -> None:
    payload = run_b1_cli_autorun.extract_json_object_from_cli_output('{"verdict":"approve","human_review_required":false}')

    assert payload["verdict"] == "approve"


def test_extract_json_object_from_cli_output_reads_fenced_json() -> None:
    payload = run_b1_cli_autorun.extract_json_object_from_cli_output(
        '```json\n{"status":"completed","files_changed":[],"commands_run":[],"blocker_found":null,"conditions_followed":[],"out_of_scope_changes_avoided":true,"notes":"ok"}\n```'
    )

    assert payload["status"] == "completed"


def test_extract_json_object_from_cli_output_ignores_trailing_logs() -> None:
    payload = run_b1_cli_autorun.extract_json_object_from_cli_output(
        '{"verdict":"approve","human_review_required":false}\nWARN plugin startup noise'
    )

    assert payload["verdict"] == "approve"


def test_extract_json_object_from_cli_output_ignores_leading_logs() -> None:
    payload = run_b1_cli_autorun.extract_json_object_from_cli_output(
        'WARN startup noise\n{"verdict":"approve","human_review_required":false}'
    )

    assert payload["verdict"] == "approve"


def test_invoke_live_cli_role_uses_wrapper_and_parses_json(tmp_path: Path, monkeypatch) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("worker prompt", encoding="utf-8")

    recorded: dict[str, object] = {}

    def fake_run(cmd, *, cwd, capture_output, text, encoding, errors, check, timeout):
        recorded["cmd"] = cmd
        recorded["cwd"] = cwd
        recorded["timeout"] = timeout
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout='{"status":"completed","files_changed":[],"commands_run":["echo ok"],"blocker_found":null,"conditions_followed":[],"out_of_scope_changes_avoided":true,"notes":"ok"}',
            stderr="",
        )

    monkeypatch.setattr(run_b1_cli_autorun.subprocess, "run", fake_run)

    payload = run_b1_cli_autorun.invoke_live_cli_role(
        role="worker",
        prompt_path=prompt_file,
        workspace=tmp_path,
        timeout_seconds=45,
    )

    assert payload["status"] == "completed"
    assert recorded["cwd"] == run_b1_cli_autorun.ROOT
    assert recorded["timeout"] == 45
    assert recorded["cmd"] == [
        run_b1_cli_autorun.PYTHON_BIN,
        str(run_b1_cli_autorun.ROLE_WRAPPER_PATH),
        "--prompt-file",
        str(prompt_file),
        "--cd",
        str(tmp_path),
        "--mode",
        "worker",
    ]


def test_coordinator_reports_role_timeout_for_live_cli(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    def fake_invoke_live_cli_role(*, role, prompt_path, workspace, timeout_seconds):
        if role == "planner":
            return {
                "run_id": "run-timeout",
                "slice_id": "B1-timeout-001",
                "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                "external_research_required": True,
                "external_research_omitted_reason": None,
                "in_scope_files": ["scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py"],
                "out_of_scope": ["app/runtime/**"],
                "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                "stop_conditions": ["human_review_required"],
            }
        raise run_b1_cli_autorun.RoleExecutionTimeoutError(f"CLI role {role} timed out after {timeout_seconds}s")

    monkeypatch.setattr(run_b1_cli_autorun, "invoke_live_cli_role", fake_invoke_live_cli_role)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="live_cli",
        role_timeout_seconds=12,
        dirty_policy="stop",
        max_slices=1,
    )

    assert result["status"] == "blocked"
    assert result["stop_reason"] == "role_timeout"
    assert result["role"] == "evaluator"


def test_coordinator_uses_role_specific_default_timeout(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    observed_timeouts: list[tuple[str, int]] = []

    def fake_invoke_live_cli_role(*, role, prompt_path, workspace, timeout_seconds):
        observed_timeouts.append((role, timeout_seconds))
        if role == "planner":
            return {
                "run_id": "run-default-timeout",
                "slice_id": "B1-timeout-default-001",
                "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                "external_research_required": True,
                "external_research_omitted_reason": None,
                "in_scope_files": ["scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py"],
                "out_of_scope": ["app/runtime/**"],
                "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                "stop_conditions": ["human_review_required"],
            }
        raise run_b1_cli_autorun.RoleExecutionTimeoutError(f"CLI role {role} timed out after {timeout_seconds}s")

    monkeypatch.setattr(run_b1_cli_autorun, "invoke_live_cli_role", fake_invoke_live_cli_role)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="live_cli",
        role_timeout_seconds=None,
        dirty_policy="stop",
        max_slices=1,
    )

    assert result["status"] == "blocked"
    assert observed_timeouts[0] == ("planner", run_b1_cli_autorun.DEFAULT_ROLE_TIMEOUT_SECONDS_BY_ROLE["planner"])
    assert observed_timeouts[1] == ("evaluator", run_b1_cli_autorun.DEFAULT_ROLE_TIMEOUT_SECONDS_BY_ROLE["evaluator"])


def test_coordinator_prefers_role_specific_timeout_override_over_global(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    observed_timeouts: list[tuple[str, int]] = []

    def fake_invoke_live_cli_role(*, role, prompt_path, workspace, timeout_seconds):
        observed_timeouts.append((role, timeout_seconds))
        if role == "planner":
            return {
                "run_id": "run-override-timeout",
                "slice_id": "B1-timeout-override-001",
                "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                "external_research_required": True,
                "external_research_omitted_reason": None,
                "in_scope_files": ["scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py"],
                "out_of_scope": ["app/runtime/**"],
                "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                "stop_conditions": ["human_review_required"],
            }
        raise run_b1_cli_autorun.RoleExecutionTimeoutError(f"CLI role {role} timed out after {timeout_seconds}s")

    monkeypatch.setattr(run_b1_cli_autorun, "invoke_live_cli_role", fake_invoke_live_cli_role)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="live_cli",
        role_timeout_seconds=12,
        role_timeout_overrides={"planner": 5},
        dirty_policy="stop",
        max_slices=1,
    )

    assert result["status"] == "blocked"
    assert observed_timeouts[0] == ("planner", 5)
    assert observed_timeouts[1] == ("evaluator", 12)


def test_main_builds_role_specific_timeout_overrides(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_autorun(**kwargs):
        captured.update(kwargs)
        return {"status": "stopped", "stop_reason": "stop", "run_dir": str(tmp_path / "run")}

    monkeypatch.setattr(run_b1_cli_autorun, "run_autorun", fake_run_autorun)

    exit_code = run_b1_cli_autorun.main(
        [
            "--workspace",
            str(tmp_path),
            "--run-root",
            str(tmp_path / "artifacts"),
            "--role-execution-mode",
            "noop_cli",
            "--role-timeout-seconds",
            "20",
            "--planner-timeout-seconds",
            "7",
            "--worker-timeout-seconds",
            "45",
            "--run-id",
            "cli-timeout-test",
        ]
    )

    assert exit_code == 0
    assert captured["role_timeout_seconds"] == 20
    assert captured["role_timeout_overrides"] == {"planner": 7, "worker": 45}

    stdout = capsys.readouterr().out
    assert '"status": "stopped"' in stdout


def test_resume_run_id_continues_from_timed_out_worker(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    phase = {"value": "initial"}
    observed_roles: list[str] = []

    def fake_invoke_live_cli_role(*, role, prompt_path, workspace, timeout_seconds):
        observed_roles.append(f"{phase['value']}:{role}")
        if phase["value"] == "initial":
            if role == "planner":
                return {
                    "run_id": "resume-run",
                    "slice_id": "B1-resume-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                }
            if role == "evaluator":
                return {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Proceed if this stays bounded.",
                    "ux_journey_rationale": "No live UX behavior changes.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep the slice bounded."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep the slice bounded."],
                    "approval_rationale": "Conditions preserve bounded execution.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["eval_only"],
                }
            if role == "worker":
                raise run_b1_cli_autorun.RoleExecutionTimeoutError("CLI role worker timed out after 5s")
            raise AssertionError(f"unexpected role during initial phase: {role}")

        if role == "worker":
            return {
                "status": "completed",
                "files_changed": [],
                "commands_run": ["echo resumed worker"],
                "blocker_found": None,
                "conditions_followed": ["Keep the slice bounded."],
                "out_of_scope_changes_avoided": True,
                "notes": "Resumed from prior planner/evaluator artifacts.",
            }
        if role == "verifier":
            return {
                "result_class": "verification_incomplete",
                "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}],
                "artifact_paths": [],
                "readiness_delta": "none",
                "conditions_verified": ["Keep the slice bounded."],
                "blocker_status": "unchanged",
                "next_safe_action": "stop",
                "human_review_required": False,
            }
        raise AssertionError(f"resume should not re-run role {role}")

    monkeypatch.setattr(run_b1_cli_autorun, "invoke_live_cli_role", fake_invoke_live_cli_role)

    initial = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="live_cli",
        role_timeout_seconds=5,
        dirty_policy="stop",
        max_slices=1,
        run_id="resume-run",
    )

    assert initial["status"] == "blocked"
    assert initial["stop_reason"] == "role_timeout"
    assert initial["role"] == "worker"

    phase["value"] = "resume"

    resumed = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="live_cli",
        role_timeout_seconds=5,
        dirty_policy="stop",
        max_slices=1,
        resume_run_id="resume-run",
    )

    assert resumed["status"] == "stopped"
    assert resumed["stop_reason"] == "runtime_blocker_unchanged"
    assert observed_roles == [
        "initial:planner",
        "initial:evaluator",
        "initial:worker",
        "resume:worker",
        "resume:verifier",
    ]

    run_dir = Path(resumed["run_dir"])
    checkpoint_files = list((run_dir / "checkpoints").glob("*.json"))
    assert checkpoint_files

    ledger = json.loads((run_dir / "ledger.json").read_text(encoding="utf-8"))
    assert any(event.get("role") == "resume" for event in ledger["events"])


def test_missing_verifier_conditions_do_not_override_human_review_stop(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-human-review",
                    "slice_id": "B1-human-review-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Proceed if bounded.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Condition A", "Condition B"],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Condition A", "Condition B"],
                    "approval_rationale": "Two conditions must be checked.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["eval_only"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["echo blocked"],
                    "blocker_found": {"code": "upstream_blocker", "detail": "provider still blocked"},
                    "conditions_followed": ["Condition A", "Condition B"],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Stopped within scope.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": [],
                    "readiness_delta": "none",
                    "conditions_verified": ["Condition A"],
                    "blocker_status": "unchanged",
                    "next_safe_action": "human_review",
                    "human_review_required": True,
                },
            }
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=1,
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "human_review_required"


def test_resume_run_id_can_finalize_checkpoint_pending_round(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-checkpoint-pending",
                    "slice_id": "B1-checkpoint-pending-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "blocked"},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Proceed if bounded.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Condition A"],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Condition A"],
                    "approval_rationale": "One condition must be checked.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["eval_only"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["echo complete"],
                    "blocker_found": None,
                    "conditions_followed": ["Condition A"],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Completed within scope.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": [],
                    "readiness_delta": "none",
                    "conditions_verified": ["Condition A"],
                    "blocker_status": "unchanged",
                    "next_safe_action": "human_review",
                    "human_review_required": True,
                },
            }
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    initial = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=1,
        run_id="run-checkpoint-pending",
    )

    assert initial["status"] == "stopped"
    assert initial["stop_reason"] == "human_review_required"

    run_dir = Path(initial["run_dir"])
    checkpoint_path = run_dir / "checkpoints" / "B1-checkpoint-pending-001.json"
    assert checkpoint_path.exists()
    checkpoint_path.unlink()

    resumed = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="noop_cli",
        role_timeout_seconds=30,
        dirty_policy="stop",
        max_slices=1,
        resume_run_id="run-checkpoint-pending",
    )

    assert resumed["status"] == "stopped"
    assert resumed["stop_reason"] == "human_review_required"
    assert checkpoint_path.exists()


def test_runtime_blocker_stop_reason_normalizes_and_writes_summary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-runtime-unchanged",
                    "slice_id": "B1-runtime-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "BuilderSpace connect error persists."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Runtime-only repair attempt.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe runtime-only attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py"],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "ConnectError remains."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Collected provider/runtime evidence only.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": ["artifacts/runtime_probe_001.json"],
                    "readiness_delta": "unchanged",
                    "conditions_verified": ["Keep this runtime-only."],
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
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=1,
        run_id="run-runtime-unchanged",
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "runtime_blocker_unchanged"

    run_dir = Path(result["run_dir"])
    summary_path = run_dir / "summaries" / "B1-runtime-001.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["blocker_family"] == "provider_connectivity"
    assert summary["evidence_tier"] == 2
    assert summary["repair_scope"] == "local_runtime_repair"
    assert summary["stop_class"] == "runtime_blocker_unchanged"
    assert summary["another_unattended_attempt_allowed"] is True


def test_two_consecutive_runtime_blocker_unchanged_attempts_stop_as_stalled(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-runtime-stalled",
                    "slice_id": "B1-runtime-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "ConnectError remains."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "First runtime repair attempt.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe first attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py --attempt 1"],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "ConnectError remains."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Attempt 1 unchanged.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": ["artifacts/runtime_probe_001.json"],
                    "readiness_delta": "unchanged",
                    "conditions_verified": ["Keep this runtime-only."],
                    "blocker_status": "unchanged",
                    "next_safe_action": "continue",
                    "human_review_required": False,
                },
            },
            {
                "planner": {
                    "run_id": "run-runtime-stalled",
                    "slice_id": "B1-runtime-002",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "ConnectError remains after attempt 1."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Second runtime repair attempt.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe second attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py --attempt 2"],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "ConnectError still remains."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "notes": "Attempt 2 unchanged.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": ["artifacts/runtime_probe_002.json"],
                    "readiness_delta": "unchanged",
                    "conditions_verified": ["Keep this runtime-only."],
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
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=2,
        run_id="run-runtime-stalled",
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "runtime_blocker_stalled"

    run_dir = Path(result["run_dir"])
    summary_path = run_dir / "summaries" / "B1-runtime-002.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["attempt_index"] == 2
    assert summary["stop_class"] == "runtime_blocker_stalled"
    assert summary["another_unattended_attempt_allowed"] is False


def test_provider_connectivity_lane_rewrites_stale_readiness_command_to_canonical_bundle(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-provider-lane",
                    "slice_id": "B1-runtime-lane-001",
                    "first_blocker": {
                        "code": "provider_runtime_connect_error_pre_trace",
                        "detail": "BuilderSpace still fails with ConnectError before any trace completes.",
                    },
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": [
                        "python scripts/verify_wave1_phase_b_tool_loop_readiness.py --report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json"
                    ],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Stay inside the runtime-only BuilderSpace repair lane.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe bounded runtime-only attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": [
                        "$env:PYTHONPATH='.'; pytest tests/test_builderspace_adapter.py -q -k \"connect_error or timeout or retry\"",
                        "$env:PYTHONPATH='.'; pytest tests/test_wave1_phase_b_minimal_tool_loop_smoke.py -q -k \"targeted_connect_error or persistent_connect_error or full_connect_error\"",
                        "python scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py --mode natural-probe --cases B1-004 --provider-profile-id builderspace-grok-4-fast-b1004-probe",
                        "python scripts/verify_wave1_phase_b_tool_loop_readiness.py --phase-b-report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json",
                    ],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "ConnectError remains."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "repair_scope": "local_runtime_repair",
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "evidence_basis": ["artifacts/runtime_probe_provider_lane.json"],
                    "notes": "Ran the canonical provider-connectivity verification bundle.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [
                        {
                            "command": "python scripts/verify_wave1_phase_b_tool_loop_readiness.py --phase-b-report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json",
                            "result": "fail",
                        }
                    ],
                    "artifact_paths": ["artifacts/runtime_probe_provider_lane.json"],
                    "readiness_delta": "unchanged",
                    "conditions_verified": ["Keep this runtime-only."],
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "repair_scope": "local_runtime_repair",
                    "repair_budget_remaining": 2,
                    "blocker_status": "unchanged",
                    "stop_class": "runtime_blocker_unchanged",
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
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=1,
        run_id="run-provider-lane",
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "runtime_blocker_unchanged"

    run_dir = Path(result["run_dir"])
    evaluator_prompt = (run_dir / "prompts" / "00_evaluator.md").read_text(encoding="utf-8")
    worker_prompt = (run_dir / "prompts" / "00_worker.md").read_text(encoding="utf-8")
    verifier_prompt = (run_dir / "prompts" / "00_verifier.md").read_text(encoding="utf-8")
    assert '"blocker_family": "provider_connectivity"' in evaluator_prompt
    assert '"repair_scope": "local_runtime_repair"' in evaluator_prompt
    assert f'"repair_lane_id": "{run_b1_cli_autorun.PROVIDER_CONNECTIVITY_LANE_ID}"' in evaluator_prompt
    assert "--phase-b-report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json" in worker_prompt
    assert "--phase-b-report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json" in verifier_prompt
    assert "--report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json" not in worker_prompt
    assert "--report artifacts/wave1_phase_b_minimal_tool_loop_smoke.json" not in verifier_prompt


def test_runtime_budget_exhausted_stops_after_max_attempts(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-runtime-budget",
                    "slice_id": "B1-runtime-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "ConnectError remains."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "First runtime repair attempt.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe first attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py --attempt 1"],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "Connectivity improved but not yet stable."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "repair_scope": "local_runtime_repair",
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "evidence_basis": ["artifacts/runtime_probe_001.json"],
                    "notes": "Attempt 1 moved the blocker.",
                },
                "verifier": {
                    "result_class": "fixed",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}],
                    "artifact_paths": ["artifacts/runtime_probe_001.json"],
                    "readiness_delta": "partial_improvement",
                    "conditions_verified": ["Keep this runtime-only."],
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "repair_scope": "local_runtime_repair",
                    "repair_budget_remaining": 2,
                    "blocker_status": "moved",
                    "stop_class": "completed_slice_continue_allowed",
                    "next_safe_action": "continue",
                    "human_review_required": False,
                },
            },
            {
                "planner": {
                    "run_id": "run-runtime-budget",
                    "slice_id": "B1-runtime-002",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "Transport still flaky."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Second runtime repair attempt.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe second attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py --attempt 2"],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "Structured transport moved the blocker again."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "repair_scope": "global_runtime_policy_repair",
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "evidence_basis": ["artifacts/runtime_probe_002.json"],
                    "notes": "Attempt 2 moved the blocker again.",
                },
                "verifier": {
                    "result_class": "fixed",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "pass"}],
                    "artifact_paths": ["artifacts/runtime_probe_002.json"],
                    "readiness_delta": "partial_improvement",
                    "conditions_verified": ["Keep this runtime-only."],
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "repair_scope": "global_runtime_policy_repair",
                    "repair_budget_remaining": 1,
                    "blocker_status": "moved",
                    "stop_class": "completed_slice_continue_allowed",
                    "next_safe_action": "continue",
                    "human_review_required": False,
                },
            },
            {
                "planner": {
                    "run_id": "run-runtime-budget",
                    "slice_id": "B1-runtime-003",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "No further movement after retries."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Third runtime repair attempt within capped budget.",
                    "ux_journey_rationale": "No UX drift.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Safe third attempt.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract", "provider_profile"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py --attempt 3"],
                    "blocker_found": {"code": "provider_runtime_connect_error", "detail": "ConnectError remains after capped attempts."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "repair_scope": "global_runtime_policy_repair",
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "evidence_basis": ["artifacts/runtime_probe_003.json"],
                    "notes": "Attempt 3 unchanged.",
                },
                "verifier": {
                    "result_class": "verification_incomplete",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": ["artifacts/runtime_probe_003.json"],
                    "readiness_delta": "unchanged",
                    "conditions_verified": ["Keep this runtime-only."],
                    "blocker_family": "provider_runtime",
                    "evidence_tier": 2,
                    "repair_scope": "global_runtime_policy_repair",
                    "repair_budget_remaining": 0,
                    "blocker_status": "unchanged",
                    "next_safe_action": "stop",
                    "human_review_required": False,
                },
            },
        ]
    }
    scenario_path = _write_mock_scenario(tmp_path, scenario)

    result = run_b1_cli_autorun.run_autorun(
        workspace=workspace,
        run_root=tmp_path / "artifacts",
        role_execution_mode="mock",
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=3,
        run_id="run-runtime-budget",
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "runtime_budget_exhausted"

    run_dir = Path(result["run_dir"])
    summary_path = run_dir / "summaries" / "B1-runtime-003.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["attempt_index"] == 3
    assert summary["repair_budget_remaining"] == 0
    assert summary["stop_class"] == "runtime_budget_exhausted"
    assert summary["another_unattended_attempt_allowed"] is False


def test_semantic_boundary_touched_hard_stops(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _init_git_repo(workspace)

    scenario = {
        "rounds": [
            {
                "planner": {
                    "run_id": "run-semantic-boundary",
                    "slice_id": "B1-runtime-semantic-001",
                    "first_blocker": {"code": "provider_runtime_blocker", "detail": "Structured transport is failing."},
                    "repo_truth_refs": ["docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md"],
                    "external_refs_checked": ["https://openai.com/index/harness-engineering/"],
                    "external_research_required": True,
                    "external_research_omitted_reason": None,
                    "in_scope_files": ["scripts/run_b1_cli_autorun.py"],
                    "out_of_scope": ["app/runtime/**"],
                    "verification_commands": ["pytest tests/test_b1_cli_autorun.py -q"],
                    "stop_conditions": ["human_review_required", "semantic_boundary_touched"],
                },
                "evaluator": {
                    "verdict": "approve_with_conditions",
                    "architecture_rationale": "Attempt a runtime-only repair first.",
                    "ux_journey_rationale": "No UX drift unless semantic boundary is crossed.",
                    "narrowed_boundary": None,
                    "human_review_required": False,
                    "attack_findings": {
                        "must_block": [],
                        "approve_condition": ["Keep this runtime-only."],
                        "cleanup_debt": [],
                    },
                    "conditions": ["Keep this runtime-only."],
                    "approval_rationale": "Runtime-only attempt is safe until semantics are implicated.",
                    "checked_context_packs": ["Current Repo Truth"],
                    "architecture_boundary_touched": ["runtime_contract"],
                },
                "worker": {
                    "status": "blocked",
                    "files_changed": [],
                    "commands_run": ["python targeted_probe.py --semantic-check"],
                    "blocker_found": {"code": "clarification_vs_estimate_policy", "detail": "Repair would require changing clarification semantics."},
                    "conditions_followed": ["Keep this runtime-only."],
                    "out_of_scope_changes_avoided": True,
                    "repair_scope": "local_runtime_repair",
                    "blocker_family": "product_semantics",
                    "evidence_tier": 2,
                    "evidence_basis": ["artifacts/runtime_probe_semantic.json"],
                    "notes": "Runtime-only repair is no longer sufficient.",
                },
                "verifier": {
                    "result_class": "semantic_ambiguity_reached",
                    "tests_run": [{"command": "pytest tests/test_b1_cli_autorun.py -q", "result": "fail"}],
                    "artifact_paths": ["artifacts/runtime_probe_semantic.json"],
                    "readiness_delta": "unchanged",
                    "conditions_verified": ["Keep this runtime-only."],
                    "blocker_family": "product_semantics",
                    "evidence_tier": 2,
                    "repair_scope": "none",
                    "repair_budget_remaining": 2,
                    "blocker_status": "semantic_boundary_touched",
                    "next_safe_action": "human_review",
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
        role_timeout_seconds=30,
        mock_scenario_path=scenario_path,
        dirty_policy="stop",
        max_slices=1,
        run_id="run-semantic-boundary",
    )

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "semantic_boundary_touched"

    run_dir = Path(result["run_dir"])
    summary_path = run_dir / "summaries" / "B1-runtime-semantic-001.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["blocker_family"] == "product_semantics"
    assert summary["stop_class"] == "semantic_boundary_touched"
    assert summary["another_unattended_attempt_allowed"] is False


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
