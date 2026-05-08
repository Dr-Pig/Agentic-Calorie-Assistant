from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pytest

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _ready_claim_boundary() -> dict[str, object]:
    return {
        "status": "ready_for_runtime_and_browser_claims",
        "runtime_backed_claim_ready": True,
        "browser_executed_claim_ready": True,
        "required_manager_runtime_gates": ["rt6_bootstrap_no_plan_body_closure"],
        "green_manager_runtime_gates": ["rt6_bootstrap_no_plan_body_closure"],
        "non_green_manager_runtime_gates": [],
    }


def _ready_today_macro_mirror_gate() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_today_macro_mirror_gate",
        "status": "today_macro_mirror_gate_ready_for_human_review",
        "pass_type": "contract",
        "frontend_semantic_owner": False,
        "frontend_calculates_macro_values": False,
        "summary": {
            "renderer_contract_fields_checked": 5,
            "visible_case_checked": True,
            "guarded_case_checked": True,
        },
    }


def _ready_body_observation_same_truth_gate() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_body_observation_same_truth_gate",
        "status": "body_observation_same_truth_gate_ready_for_human_review",
        "pass_type": "browser_executed",
        "upstream_runtime_gate": "rt6_bootstrap_no_plan_body_closure",
        "summary": {
            "required_browser_flag_count": 7,
            "all_required_browser_flags_true": True,
            "upstream_gate_green": True,
        },
    }


def _ready_bootstrap_same_truth_gate() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_bootstrap_same_truth_gate",
        "status": "bootstrap_same_truth_gate_ready_for_human_review",
        "pass_type": "browser_executed",
        "upstream_runtime_gate": "rt6_bootstrap_no_plan_body_closure",
        "summary": {
            "required_browser_flag_count": 10,
            "all_required_browser_flags_true": True,
            "upstream_gate_green": True,
        },
    }


def _ready_clarify_commit_correction_same_truth_gate() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_clarify_commit_correction_same_truth_gate",
        "status": "clarify_commit_correction_same_truth_gate_ready_for_human_review",
        "pass_type": "browser_executed",
        "upstream_runtime_gate": "rt7_clarify_commit_correction_closure",
        "summary": {
            "required_short_term_context_flag_count": 9,
            "required_target_candidate_flag_count": 5,
            "required_fixture_step_count": 8,
            "target_candidate_count_rendered": 2,
            "completed_fixture_step_count": 8,
            "upstream_gate_green": True,
        },
    }


def _required_payloads() -> dict[str, dict[str, object]]:
    return {
        "phase_c_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "phase_c_same_truth_gate",
            "status": "pass",
        },
        "accurate_intake_mvp_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "accurate_intake_mvp_deterministic_v1",
            "status": "pass",
        },
        "browser_shell_smoke": {
            "artifact_schema_version": "1.0",
            "claim_scope": "local_browser_executed_shell_smoke_artifact",
            "status": "pass",
            "browser_executed": True,
        },
        "chat_history_reload_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "accurate_intake_chat_history_reload_gate_v1",
            "status": "pass",
        },
        "free_text_manual_target_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "accurate_intake_free_text_manual_target_gate",
            "status": "pass",
        },
        "dogfood_review_queue": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_dogfood_review_queue",
            "status": "generated",
        },
        "local_dogfood_data_hygiene": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_local_dogfood_data_hygiene",
            "status": "pass",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        "local_operator_data_hygiene_bundle": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "status": "local_operator_data_hygiene_ready",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: {
            "artifact_schema_version": "1.0",
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE,
            "status": CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "real_fooddb_pass_claimed": False,
            "private_self_use_approved": False,
        },
        "product_pages_self_use_flow_gate": {
            "artifact_schema_version": "1.0",
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
            "status": "product_pages_self_use_flow_ready_for_human_review",
            "pass_type": "contract",
            "current_shell_sync_contract_source": "docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml",
            "manager_runtime_gate_ledger_source": "docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml",
            "appshell_claim_boundary": _ready_claim_boundary(),
            "summary": {
                "three_distinct_pages_verified": True,
                "seven_day_diary_checked": True,
                "short_term_context_checked": True,
                "target_candidate_ui_checked": True,
            },
        },
        "ui_context_alignment_pack": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_ui_context_alignment_pack",
            "status": "ui_context_alignment_ready_for_human_review",
            "summary": {
                "chat_context_reload_checked": True,
                "seven_day_diary_checked": True,
                "body_read_model_checked": True,
            },
        },
        "today_macro_mirror_gate": _ready_today_macro_mirror_gate(),
        "bootstrap_same_truth_gate": _ready_bootstrap_same_truth_gate(),
        "body_observation_same_truth_gate": _ready_body_observation_same_truth_gate(),
        "clarify_commit_correction_same_truth_gate": _ready_clarify_commit_correction_same_truth_gate(),
        "browser_activation_evidence_gate": {
            "artifact_schema_version": "1.0",
            "artifact_type": CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
            "status": "browser_activation_evidence_ready_for_human_review",
            "pass_type": "contract",
            "current_shell_sync_contract_source": "docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml",
            "manager_runtime_gate_ledger_source": "docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml",
            "appshell_claim_boundary": _ready_claim_boundary(),
            "all_required_browser_artifacts_executed": True,
            "browser_executed_required": True,
        },
        "manager_tool_surface_inventory": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_manager_tool_surface_inventory",
            "status": "manager_tool_surface_inventory_ready_for_human_review",
            "required_direct_lane_ids": [f"lane-{index}" for index in range(7)],
            "required_manager_tools": [f"tool-{index}" for index in range(10)],
            "summary": {
                "direct_lane_count": 7,
                "target_tool_count": 10,
                "mutation_bearing_lane_count": 4,
                "read_only_tool_count": 6,
            },
        },
        "non_fooddb_manager_tool_contract": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_non_fooddb_manager_tool_contract",
            "status": "non_fooddb_manager_tool_contract_ready_for_human_review",
            "summary": {
                "inventory_backed_tool_count": 10,
                "read_only_tool_count": 7,
                "proposal_tool_count": 1,
                "mutation_tool_count": 3,
                "legacy_direct_route_debt_count": 1,
                "direct_lane_bridge_count": 7,
            },
        },
        "manager_tool_choice_regression_wall": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_manager_tool_choice_regression_wall",
            "status": "manager_tool_choice_regression_wall_pass",
            "semantic_owner": "fixture_manager_structured_decision",
            "summary": {"case_count": 11},
        },
        "context_conditioned_intent_wall": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_conditioned_intent_wall",
            "status": "pass",
            "manager_fixture_semantic_source_used": True,
            "summary": {"scenario_count": 11},
        },
        "non_fooddb_read_only_tool_loop_fake_smoke": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke",
            "status": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
            "summary": {"case_count": 6},
        },
        "non_fooddb_mutation_tool_guard_smoke": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_non_fooddb_mutation_tool_guard_smoke",
            "status": "non_fooddb_mutation_tool_guard_smoke_pass",
            "summary": {"case_count": 10},
        },
        "manager_intent_readiness_review_pack": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_manager_intent_readiness_review_pack",
            "status": "manager_intent_readiness_ready_for_human_review",
            "review_required_before_provider_call": True,
            "semantic_owner": "fixture_manager_structured_decision",
            "shared_contract_changed": False,
            "manager_context_packet_schema_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "intent_wall_scenarios": 11,
                "contextual_interactions": 11,
                "fake_provider_handoff_scenarios": 6,
                "responder_allowed_fact_scenarios": 5,
                "context_covered_capabilities": 9,
                "context_blocked_capabilities": 0,
                "context_known_runtime_gaps": 0,
                "session_pending_followup_carryover_checked": True,
                "session_target_candidate_ui_checked": True,
                "session_long_context_checked": True,
            },
        },
        "context_live_diagnostic_case_matrix": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_case_matrix",
            "status": "pass",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {"case_count": 11, "compound_cases": 1},
        },
        "context_live_diagnostic_anti_overfit_guard": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
            "status": "pass",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "fixed_case_matrix_used": True,
                "case_count": 11,
                "compound_cases": 1,
                "ambiguity_cases": 1,
            },
        },
        "context_live_diagnostic_holdout_plan": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_holdout_plan",
            "status": "pass",
            "plan_only": True,
            "fixture_only": True,
            "diagnostic_only": True,
            "local_only": True,
            "fixed_case_matrix_used": True,
            "holdout_variants_withheld_from_default_live_prompt": True,
            "ad_hoc_live_case_selection_allowed": False,
            "provider_optimized_case_selection_allowed": False,
            "blocked_if_single_case_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "fixed_case_matrix_used": True,
                "case_count": 11,
                "withheld_holdout_variant_count": 22,
                "cases_with_holdouts": 11,
                "compound_cases": 1,
                "ambiguity_cases": 1,
            },
        },
        "context_live_provider_input_preflight": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_provider_input_preflight",
            "status": "pass",
            "plan_only": True,
            "fixture_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "fixed_case_matrix_used": True,
            "response_schema_strict": True,
            "deterministic_selected_intent": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "case_count": 11,
                "blocked_input_count": 0,
                "strict_schema_input_count": 11,
                "target_candidate_inputs": 4,
                "pending_pin_inputs": 2,
            },
        },
        "context_live_response_contract_dry_run": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_response_contract_dry_run",
            "status": "pass",
            "plan_only": True,
            "fixture_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "response_schema_strict": True,
            "deterministic_selected_intent": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "case_count": 11,
                "validated_response_count": 11,
                "blocked_response_count": 0,
                "target_candidate_response_count": 4,
                "ambiguity_preserved_response_count": 1,
                "mutation_request_count": 0,
            },
        },
        "context_live_diagnostic_gate": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_gate",
            "claim_scope": "pl_ce_context_live_diagnostic_gate",
            "status": "context_live_diagnostic_gate_ready_without_live_canary",
            "review_pack_status": "context_live_diagnostic_review_ready_without_live_canary",
            "canary_status": "blocked",
            "live_provider_allowed": False,
            "live_provider_required": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fixed_case_matrix_used": True,
            "ad_hoc_live_case_selection_allowed": False,
            "anti_overfit_guard_required": True,
            "holdout_plan_required": True,
            "response_contract_dry_run_required": True,
            "diagnostic_only": True,
            "local_only": True,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "fixed_case_count": 11,
                "dry_run_validated_response_count": 11,
                "live_provider_output_count": 0,
                "live_blocked_response_count": 0,
            },
        },
    }


def _artifact_args(artifact_dir: Path, groups: tuple[str, ...]) -> list[str]:
    args: list[str] = []
    for group_id in groups:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])
    return args


def test_local_web_self_use_candidate_v2_gate_runner_writes_outputs(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _required_payloads().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"
    pre_live_output = tmp_path / "pre_live_decision_pack.json"
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(pre_live_output),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))
    pre_live_pack = json.loads(pre_live_output.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["pre_live_selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert printed["candidate_prepared"] is True
    assert pre_live_evidence["_evidence_metadata"]["status"] == "complete"
    assert pre_live_evidence["_evidence_metadata"]["local_web_candidate_gate_blocked"] is False
    assert pre_live_pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is True
    assert candidate["local_web_self_use_candidate_v2"]["candidate_prepared"] is True
    assert "private_self_use_approved" not in candidate["local_web_self_use_candidate_v2"]


def test_local_web_self_use_candidate_v2_gate_runner_keeps_distinct_default_phase_c_path() -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import DEFAULT_EVIDENCE_PATHS

    assert DEFAULT_EVIDENCE_PATHS["phase_c_gate"].name == "phase_c_gate.json"


def test_local_web_self_use_candidate_v2_gate_runner_derives_phase_c_identity_from_mvp_gate(
    tmp_path: Path,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        build_local_web_candidate_gate_evidence,
    )

    mvp_gate = {
        "artifact_schema_version": "1.0",
        "gate_id": "accurate_intake_mvp_deterministic_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass",
        "groups": [
            {"group_id": "ledger_truth_and_read_model", "status": "pass"},
        ],
    }
    mvp_path = tmp_path / "accurate_intake_mvp_gate.json"
    _write(mvp_path, mvp_gate)

    overrides = {
        group_id: tmp_path / f"missing_{group_id}.json"
        for group_id in DEFAULT_EVIDENCE_PATHS
    }
    overrides["phase_c_gate"] = tmp_path / "missing_phase_c_gate.json"
    overrides["accurate_intake_mvp_gate"] = mvp_path

    evidence = build_local_web_candidate_gate_evidence(path_overrides=overrides)

    assert evidence["_evidence_metadata"]["missing_evidence"] == [
        "browser_shell_smoke",
        "chat_history_reload_gate",
        "free_text_manual_target_gate",
        "dogfood_review_queue",
        "local_dogfood_data_hygiene",
        "local_operator_data_hygiene_bundle",
            CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
        "product_pages_self_use_flow_gate",
        "ui_context_alignment_pack",
        "today_macro_mirror_gate",
        "bootstrap_same_truth_gate",
        "body_observation_same_truth_gate",
        "clarify_commit_correction_same_truth_gate",
        "browser_activation_evidence_gate",
        "manager_tool_surface_inventory",
        "non_fooddb_manager_tool_contract",
        "manager_tool_choice_regression_wall",
        "context_conditioned_intent_wall",
        "non_fooddb_read_only_tool_loop_fake_smoke",
        "non_fooddb_mutation_tool_guard_smoke",
        "manager_intent_readiness_review_pack",
        "context_live_diagnostic_case_matrix",
        "context_live_diagnostic_anti_overfit_guard",
        "context_live_diagnostic_holdout_plan",
        "context_live_provider_input_preflight",
        "context_live_response_contract_dry_run",
        "context_live_diagnostic_gate",
    ]
    assert evidence["phase_c_gate"]["artifact_type"] == "accurate_intake_phase_c_gate_from_mvp_gate"
    assert evidence["phase_c_gate"]["status"] == "pass"
    assert evidence["phase_c_gate"]["source_gate_id"] == "accurate_intake_mvp_deterministic_v1"


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_artifact_without_autofix(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop(CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID)
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"
    pre_live_output = tmp_path / "pre_live_decision_pack.json"
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(pre_live_output),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["evidence_status"] == "blocked_missing_evidence"
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == [CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID]
    assert pre_live_evidence[CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID]["autofix_attempted"] is False
    assert (
        f"missing evidence: {CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID}"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )
    assert "local web candidate gate evidence blocked" in candidate["local_web_self_use_candidate_v2"]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_context_live_matrix(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("context_live_diagnostic_case_matrix")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["context_live_diagnostic_case_matrix"]
    assert (
        "missing evidence: context_live_diagnostic_case_matrix"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_today_macro_mirror_gate(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("today_macro_mirror_gate")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["today_macro_mirror_gate"]
    assert "missing evidence: today_macro_mirror_gate" in candidate[
        "local_web_self_use_candidate_v2"
    ]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_body_observation_same_truth_gate(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("body_observation_same_truth_gate")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["body_observation_same_truth_gate"]
    assert "missing evidence: body_observation_same_truth_gate" in candidate[
        "local_web_self_use_candidate_v2"
    ]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_clarify_commit_correction_same_truth_gate(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("clarify_commit_correction_same_truth_gate")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["clarify_commit_correction_same_truth_gate"]
    assert "missing evidence: clarify_commit_correction_same_truth_gate" in candidate[
        "local_web_self_use_candidate_v2"
    ]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_context_live_anti_overfit_guard(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("context_live_diagnostic_anti_overfit_guard")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["context_live_diagnostic_anti_overfit_guard"]
    assert (
        "missing evidence: context_live_diagnostic_anti_overfit_guard"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_context_live_holdout_plan(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("context_live_diagnostic_holdout_plan")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["context_live_diagnostic_holdout_plan"]
    assert (
        "missing evidence: context_live_diagnostic_holdout_plan"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_context_live_gate(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("context_live_diagnostic_gate")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["context_live_diagnostic_gate"]
    assert (
        "missing evidence: context_live_diagnostic_gate"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_blocks_pl_ce_overclaim(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads[CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID][
        "ready_for_live_diagnostic_decision"
    ] = True
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert (
        "CurrentShell compatibility local review overclaim"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )
    assert "private_self_use_approved" not in candidate["local_web_self_use_candidate_v2"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_blocked_appshell_claim_boundary(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["browser_activation_evidence_gate"]["appshell_claim_boundary"] = {
        "status": "blocked_on_manager_runtime_upstream_gates",
        "runtime_backed_claim_ready": False,
        "browser_executed_claim_ready": False,
        "required_manager_runtime_gates": ["rt7_clarify_commit_correction_closure"],
        "green_manager_runtime_gates": ["rt3a_react_trace_observable_skeleton"],
        "non_green_manager_runtime_gates": ["rt7_clarify_commit_correction_closure"],
    }
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert (
        "browser activation evidence gate appshell claim not ready"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_blocks_status_only_artifacts(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["phase_c_gate"] = {"status": "pass"}
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["evidence_status"] == "blocked_invalid_evidence"
    assert pre_live_evidence["_evidence_metadata"]["invalid_evidence"] == ["phase_c_gate"]
    assert "phase_c_gate_artifact_schema_version_missing" in pre_live_evidence["_evidence_metadata"]["blockers"]
    assert candidate["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "local web candidate gate evidence blocked" in candidate["local_web_self_use_candidate_v2"]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_rejects_wrong_phase_c_artifact_identity(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["phase_c_gate"] = {
        "artifact_schema_version": "1.0",
        "gate_id": "accurate_intake_mvp_deterministic_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass",
    }
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(tmp_path / "candidate.json"),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["evidence_status"] == "blocked_invalid_evidence"
    assert "phase_c_gate_artifact_identity_mismatch" in pre_live_evidence["_evidence_metadata"]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_local_operator_overclaims(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["local_operator_data_hygiene_bundle"]["production_db_touched"] = True
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert "production DB touched" in candidate["local_web_self_use_candidate_v2"]["blockers"]
    assert (
        "pre-live blocker: local_operator_data_hygiene_bundle_production_db_touched"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_rejects_bad_artifact_override_with_argparse_error(
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import main

    with pytest.raises(SystemExit) as missing_equals:
        main(["--artifact", "not_a_pair"])
    first_error = capsys.readouterr().err

    with pytest.raises(SystemExit) as unknown_group:
        main(["--artifact", "unknown_group=artifact.json"])
    second_error = capsys.readouterr().err

    assert missing_equals.value.code == 2
    assert unknown_group.value.code == 2
    assert "--artifact must be group_id=path" in first_error
    assert "Unknown local web candidate evidence group" in second_error


def test_local_web_self_use_candidate_v2_gate_runner_stays_out_of_live_fooddb_and_websearch_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_local_web_self_use_candidate_v2_gate.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "Food Evidence promotion policy",
    ):
        assert fragment not in source
    for forbidden_import in (
        "requests",
        "httpx",
        "urllib",
        "openai",
        "app.providers",
    ):
        assert forbidden_import not in imported_modules
