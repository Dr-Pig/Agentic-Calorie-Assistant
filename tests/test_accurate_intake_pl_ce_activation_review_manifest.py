from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
)
from app.composition.accurate_intake_pl_ce_activation_review_manifest import (
    build_pl_ce_activation_review_manifest_artifact,
)


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "pl_ce_local_mvp_candidate_bundle": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
            "status": "pl_ce_local_mvp_candidate_ready_for_human_review",
            "activation_gate_status": "blocked_pending_human_and_browser_activation",
            "required_inputs": [
                "ui_same_truth_contract",
                "context_quality_pack",
                "short_term_context_runtime_replay",
                "context_coverage_matrix",
                "context_live_diagnostic_case_matrix",
                "context_live_diagnostic_anti_overfit_guard",
                "context_conditioned_intent_wall",
                "context_live_diagnostic_case_matrix",
                "context_live_diagnostic_anti_overfit_guard",
                "correction_removal_fixture_flow",
                "responder_input_contract_fake_smoke",
                "fixture_packet_emulator",
                "fake_provider_tool_loop_smoke",
                "review_eval_candidate_pipeline",
                "local_operator_data_hygiene_bundle",
                "mvp_gate_summary",
            ],
            "blockers": [],
            "included_artifact_statuses": {
                "ui_same_truth_contract": {"status": "pass", "present": True},
                "context_quality_pack": {"status": "context_quality_diagnostic_pass", "present": True},
                "short_term_context_runtime_replay": {
                    "status": "runtime_replay_diagnostic_pass",
                    "present": True,
                },
                "context_coverage_matrix": {
                    "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
                    "status": "context_coverage_matrix_ready_for_human_review",
                    "present": True,
                },
                "context_live_diagnostic_case_matrix": {
                    "artifact_type": "accurate_intake_context_live_diagnostic_case_matrix",
                    "status": "pass",
                    "present": True,
                },
                "context_live_diagnostic_anti_overfit_guard": {
                    "artifact_type": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
                    "status": "pass",
                    "present": True,
                },
                "context_conditioned_intent_wall": {"status": "pass", "present": True},
                "context_live_diagnostic_case_matrix": {"status": "pass", "present": True},
                "context_live_diagnostic_anti_overfit_guard": {
                    "status": "pass",
                    "present": True,
                },
                "correction_removal_fixture_flow": {"status": "pass", "present": True},
                "responder_input_contract_fake_smoke": {"status": "pass", "present": True},
                "fixture_packet_emulator": {"status": "fixture_packet_emulator_ready", "present": True},
                "fake_provider_tool_loop_smoke": {
                    "status": "fake_provider_tool_loop_smoke_pass",
                    "present": True,
                },
                "review_eval_candidate_pipeline": {
                    "status": "review_eval_candidate_pipeline_ready",
                    "present": True,
                },
                "local_operator_data_hygiene_bundle": {
                    "status": "local_operator_data_hygiene_ready",
                    "present": True,
                },
                "mvp_gate_summary": {"status": "pass", "present": True},
            },
            "browser_gate_policy": {
                "activation_gate": {
                    "require_browser_execution": True,
                    "browser_executed_required": True,
                }
            },
            "fooddb_dependency": {
                "fooddb_artifact_status": "blocked_waiting_for_fdb_artifact",
                "ready_for_fdb_integration": False,
            },
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "review_required_before_provider_call": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "pl_ce_browser_activation_evidence_gate": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_browser_activation_evidence_gate",
            "status": "browser_activation_evidence_ready_for_human_review",
            "required_inputs": [
                "pl_ce_local_mvp_candidate_bundle",
                "product_pages_browser_smoke",
                "product_pages_seven_day_diary_smoke",
                "product_pages_short_term_context_smoke",
                "product_pages_target_candidate_ui_smoke",
                "product_pages_visual_qa",
                "fixture_full_product_loop_e2e",
            ],
            "browser_required_inputs": [
                "product_pages_browser_smoke",
                "product_pages_seven_day_diary_smoke",
                "product_pages_short_term_context_smoke",
                "product_pages_target_candidate_ui_smoke",
                "product_pages_visual_qa",
            ],
            "blockers": [],
            "included_artifact_statuses": {
                "pl_ce_local_mvp_candidate_bundle": {
                    "status": "pl_ce_local_mvp_candidate_ready_for_human_review",
                    "browser_executed": "not_applicable",
                },
                "product_pages_browser_smoke": {"status": "pass", "browser_executed": True},
                "product_pages_seven_day_diary_smoke": {
                    "status": "pass",
                    "browser_executed": True,
                },
                "product_pages_short_term_context_smoke": {
                    "status": "pass",
                    "browser_executed": True,
                },
                "product_pages_target_candidate_ui_smoke": {
                    "status": "pass",
                    "browser_executed": True,
                },
                "product_pages_visual_qa": {"status": "pass", "browser_executed": True},
                "fixture_full_product_loop_e2e": {
                    "status": "fixture_product_loop_e2e_diagnostic_pass",
                    "browser_executed": "not_applicable",
                },
            },
            "all_required_browser_artifacts_executed": True,
            "browser_executed_required": True,
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "review_required_before_provider_call": True,
            "summary": {
                "browser_artifact_count": 5,
                "browser_executed_count": 5,
                "requires_three_distinct_pages": True,
                "requires_seven_day_today_diary": True,
                "requires_short_term_context_render": True,
                "requires_target_candidate_ui": True,
                "requires_fixture_full_product_loop_e2e": True,
                "requires_visual_qa": True,
                "requires_no_debug_trace_leak": True,
                "fixture_product_loop_step_count": 10,
            },
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "pl_ce_ui_context_alignment_pack": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_ui_context_alignment_pack",
            "status": "ui_context_alignment_ready_for_human_review",
            "required_inputs": [
                "ui_same_truth_contract",
                "product_pages_renderer_source_map",
                "context_coverage_matrix",
                "product_pages_browser_smoke",
                "product_pages_seven_day_diary_smoke",
                "product_pages_short_term_context_smoke",
                "product_pages_visual_qa",
            ],
            "blockers": [],
            "included_artifact_statuses": {
                "ui_same_truth_contract": {"status": "pass", "present": True},
                "product_pages_renderer_source_map": {
                    "status": "product_pages_renderer_source_map_ready_for_human_review",
                    "present": True,
                },
                "context_coverage_matrix": {
                    "status": "context_coverage_matrix_ready_for_human_review",
                    "present": True,
                },
                "product_pages_browser_smoke": {"status": "pass", "browser_executed": True},
                "product_pages_seven_day_diary_smoke": {
                    "status": "pass",
                    "browser_executed": True,
                },
                "product_pages_short_term_context_smoke": {
                    "status": "pass",
                    "browser_executed": True,
                },
                "product_pages_visual_qa": {"status": "pass", "browser_executed": True},
            },
            "summary": {
                "pages_verified": ["chat", "today", "body"],
                "context_covered_capabilities": 9,
                "context_known_runtime_gap_count": 0,
                "renderer_source_map_page_count": 3,
                "renderer_source_map_selector_count": 33,
                "renderer_source_map_endpoint_count": 8,
                "seven_day_diary_checked": True,
                "chat_context_reload_checked": True,
                "body_read_model_checked": True,
            },
            "aggregate_only": True,
            "self_generated_evidence_used": False,
            "human_review_required": True,
            "review_required_before_provider_call": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "context_live_diagnostic_holdout_plan": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_holdout_plan",
            "status": "pass",
            "claim_scope": "pl_ce_context_live_diagnostic_holdout_overfit_control",
            "diagnostic_only": True,
            "fixture_only": True,
            "plan_only": True,
            "local_only": True,
            "fixed_case_matrix_used": True,
            "holdout_variants_withheld_from_default_live_prompt": True,
            "ad_hoc_live_case_selection_allowed": False,
            "provider_optimized_case_selection_allowed": False,
            "blocked_if_single_case_only": True,
            "human_review_required_before_promoting_failures": True,
            "semantic_owner": "future_live_manager_provider_when_human_approved",
            "deterministic_role": "validate_case_selection_not_select_intent",
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "ready_for_live_diagnostic_decision": False,
            "fooddb_used": False,
            "fooddb_evidence_used": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "readiness_claimed": False,
            "blockers": [],
            "summary": {
                "case_count": len(REQUIRED_CASE_IDS),
                "fixed_case_count": len(REQUIRED_CASE_IDS),
                "holdout_variant_count": len(REQUIRED_CASE_IDS) * 2,
                "withheld_holdout_variant_count": len(REQUIRED_CASE_IDS) * 2,
                "cases_with_holdouts": len(REQUIRED_CASE_IDS),
                "case_ids": list(REQUIRED_CASE_IDS),
                "compound_cases": 1,
                "ambiguity_cases": 3,
                "pending_pin_cases": 2,
                "target_candidate_cases": 4,
            },
        },
        "context_live_diagnostic_dry_run_evaluator": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_dry_run_evaluator",
            "status": "pass",
            "claim_scope": "pl_ce_context_live_diagnostic_fixture_evaluator",
            "diagnostic_only": True,
            "fixture_only": True,
            "plan_only": True,
            "local_only": True,
            "fixed_case_matrix_used": True,
            "semantic_owner": "fixture_manager_structured_decision",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": [],
            "summary": {
                "case_count": len(REQUIRED_CASE_IDS),
                "evaluated_case_count": len(REQUIRED_CASE_IDS),
                "blocked_case_count": 0,
                "target_candidate_cases": 4,
                "pending_pin_cases": 2,
                "ambiguity_cases": 3,
            },
        },
        "context_live_response_contract_dry_run": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_response_contract_dry_run",
            "status": "pass",
            "claim_scope": "pl_ce_context_live_response_contract_dry_run",
            "diagnostic_only": True,
            "fixture_only": True,
            "plan_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "full_matrix_required": True,
            "semantic_owner": "fixture_manager_structured_decision_for_dry_run_only",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": [],
            "summary": {
                "case_count": len(REQUIRED_CASE_IDS),
                "validated_response_count": len(REQUIRED_CASE_IDS),
                "blocked_response_count": 0,
                "target_candidate_response_count": 4,
                "ambiguity_preserved_response_count": 3,
            },
        },
    }


def _context_live_review_pack(*, live: bool = True) -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_context_live_diagnostic_review_pack",
        "status": (
            "context_live_diagnostic_review_ready_with_live_canary"
            if live
            else "context_live_diagnostic_review_ready_without_live_canary"
        ),
        "claim_scope": "pl_ce_context_live_diagnostic_review_for_human_review_only",
        "blockers": [],
        "diagnostic_only": True,
        "aggregate_only": True,
        "human_review_required": True,
        "review_required_before_provider_activation": True,
        "fixed_case_matrix_used": True,
        "blocked_live_canary_is_not_pass": True,
        "live_canary_status": "live_diagnostic_pass" if live else "not_invoked",
        "live_llm_invoked": live,
        "live_provider_invoked": live,
        "semantic_owner": "live_manager_provider" if live else "not_invoked",
        "ready_for_live_diagnostic_decision": False,
        "ready_for_fdb_integration": False,
        "fooddb_used": False,
        "fooddb_evidence_used": False,
        "web_tavily_used": False,
        "websearch_evidence_used": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_packet_schema_changed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "readiness_claimed": False,
        "summary": {
            "fixed_case_count": len(REQUIRED_CASE_IDS),
            "dry_run_validated_response_count": len(REQUIRED_CASE_IDS),
            "dry_run_blocked_response_count": 0,
            "anti_overfit_distinct_intent_count": 11,
            "anti_overfit_holdout_variant_count": 22,
            "live_provider_input_count": len(REQUIRED_CASE_IDS) if live else 0,
            "live_provider_output_count": len(REQUIRED_CASE_IDS) if live else 0,
            "live_blocked_response_count": 0,
            "live_target_candidate_response_count": 4 if live else 0,
            "live_ambiguity_preserved_response_count": 1 if live else 0,
        },
        "context_live_diagnostic_stage_summary": {
            "live_stage": "full-matrix" if live else "not_invoked",
            "live_stage_reason": "full_matrix_provider_outputs" if live else "not_invoked",
            "live_provider_output_count": len(REQUIRED_CASE_IDS) if live else 0,
            "live_blocked_response_count": 0,
            "single_case_live_probe_completed": False,
            "full_matrix_live_probe_completed": live,
            "diagnostic_only_not_readiness": True,
        },
    }


def _context_live_gate(*, live: bool = True) -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_context_live_diagnostic_gate",
        "status": (
            "context_live_diagnostic_gate_ready_with_live_canary"
            if live
            else "context_live_diagnostic_gate_ready_without_live_canary"
        ),
        "claim_scope": "pl_ce_context_live_diagnostic_gate",
        "blockers": [],
        "review_pack_status": (
            "context_live_diagnostic_review_ready_with_live_canary"
            if live
            else "context_live_diagnostic_review_ready_without_live_canary"
        ),
        "canary_status": "live_diagnostic_pass" if live else "not_invoked",
        "live_llm_invoked": live,
        "live_provider_invoked": live,
        "live_provider_allowed": live,
        "live_provider_required": live,
        "live_stage": "full-matrix" if live else "single-case",
        "stage_gate_status": "context_live_full_matrix_probe_pass" if live else "not_applicable",
        "full_matrix_live_probe_required": True,
        "ad_hoc_live_case_selection_allowed": False,
        "fixed_case_matrix_used": True,
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
        "readiness_claimed": False,
        "artifact_paths": {
            "context_live_diagnostic_case_matrix": "artifacts/case_matrix.json",
            "context_live_diagnostic_anti_overfit_guard": "artifacts/anti_overfit.json",
            "context_live_diagnostic_holdout_plan": "artifacts/holdout_plan.json",
            "context_live_provider_input_preflight": "artifacts/preflight.json",
            "context_live_response_contract_dry_run": "artifacts/dry_run.json",
            "context_live_diagnostic_canary": "artifacts/canary.json",
            "context_live_diagnostic_review_pack": "artifacts/review_pack.json",
            "context_live_diagnostic_stage_gate": "artifacts/stage_gate.json",
        },
        "summary": {
            "fixed_case_count": len(REQUIRED_CASE_IDS),
            "dry_run_validated_response_count": len(REQUIRED_CASE_IDS),
            "live_provider_output_count": len(REQUIRED_CASE_IDS) if live else 0,
            "live_blocked_response_count": 0,
        },
    }


def test_activation_review_manifest_summarizes_human_review_ready_evidence_only() -> None:
    artifact = build_pl_ce_activation_review_manifest_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_activation_review_manifest"
    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["aggregate_only"] is True
    assert artifact["self_generated_evidence_used"] is False
    assert artifact["human_review_required"] is True
    assert artifact["live_diagnostic_human_approval_required"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert artifact["web_readiness_claimed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["review_checkpoints"]["local_mvp_candidate_bundle"] == "ready_for_human_review"
    assert artifact["review_checkpoints"]["browser_activation_evidence_gate"] == "ready_for_human_review"
    assert artifact["review_checkpoints"]["ui_context_alignment_pack"] == "ready_for_human_review"
    assert artifact["review_checkpoints"]["context_live_diagnostic_holdout_plan"] == "pass"
    assert artifact["review_checkpoints"]["context_live_diagnostic_dry_run_evaluator"] == "pass"
    assert artifact["review_checkpoints"]["context_live_response_contract_dry_run"] == "pass"
    assert artifact["included_artifact_statuses"]["pl_ce_ui_context_alignment_pack"]["status"] == (
        "ui_context_alignment_ready_for_human_review"
    )
    assert artifact["remaining_stop_gates"]["fooddb_artifact_status"] == "blocked_waiting_for_fdb_artifact"
    assert artifact["remaining_stop_gates"]["live_provider_status"] == "blocked_pending_human_approval"
    assert (
        artifact["remaining_stop_gates"]["context_live_holdout_plan_status"]
        == "passed_holdout_plan_only"
    )
    assert artifact["remaining_stop_gates"]["context_live_dry_run_status"] == "passed_fixture_dry_run_only"
    assert (
        artifact["remaining_stop_gates"]["context_live_response_contract_status"]
        == "passed_fixture_response_contract_only"
    )
    assert artifact["blockers"] == []


def test_activation_review_manifest_accepts_optional_context_live_review_pack_without_readiness_claim() -> None:
    inputs = _valid_inputs()
    inputs["context_live_diagnostic_review_pack"] = _context_live_review_pack(live=True)

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["review_checkpoints"]["context_live_diagnostic_review_pack"] == "live_canary_passed"
    assert (
        artifact["remaining_stop_gates"]["context_live_provider_status"]
        == "context_only_live_diagnostic_passed_not_full_e2e"
    )
    assert artifact["live_diagnostic_evidence_present"] is True
    assert artifact["upstream_live_llm_invoked"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_called"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["context_live_diagnostic_stage_summary"] == {
        "live_stage": "full-matrix",
        "stage_gate_status": "review_pack_full_matrix_live_diagnostic_pass",
        "live_provider_output_count": len(REQUIRED_CASE_IDS),
        "live_blocked_response_count": 0,
        "full_matrix_live_probe_completed": True,
        "single_case_live_probe_completed": False,
        "diagnostic_only_not_readiness": True,
    }
    assert artifact["blockers"] == []


def test_activation_review_manifest_summarizes_single_case_context_live_review_pack() -> None:
    inputs = _valid_inputs()
    review_pack = _context_live_review_pack(live=True)
    review_pack["context_live_diagnostic_stage_summary"] = {
        "live_stage": "single-case",
        "live_stage_reason": "single_provider_output",
        "live_provider_output_count": 1,
        "live_blocked_response_count": 0,
        "single_case_live_probe_completed": True,
        "full_matrix_live_probe_completed": False,
        "diagnostic_only_not_readiness": True,
    }
    inputs["context_live_diagnostic_review_pack"] = review_pack

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["context_live_diagnostic_stage_summary"] == {
        "live_stage": "single-case",
        "stage_gate_status": "review_pack_single_case_live_diagnostic_pass",
        "live_provider_output_count": 1,
        "live_blocked_response_count": 0,
        "full_matrix_live_probe_completed": False,
        "single_case_live_probe_completed": True,
        "diagnostic_only_not_readiness": True,
    }
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["product_readiness_claimed"] is False


def test_activation_review_manifest_accepts_optional_context_live_gate_without_readiness_claim() -> None:
    inputs = _valid_inputs()
    inputs["context_live_diagnostic_gate"] = _context_live_gate(live=True)

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["review_checkpoints"]["context_live_diagnostic_gate"] == "gate_live_canary_passed"
    assert (
        artifact["remaining_stop_gates"]["context_live_gate_status"]
        == "context_only_live_diagnostic_gate_passed_not_full_e2e"
    )
    assert artifact["context_live_gate_evidence_present"] is True
    assert artifact["upstream_context_live_gate_llm_invoked"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_called"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["context_live_diagnostic_stage_summary"] == {
        "live_stage": "full-matrix",
        "stage_gate_status": "context_live_full_matrix_probe_pass",
        "live_provider_output_count": len(REQUIRED_CASE_IDS),
        "live_blocked_response_count": 0,
        "full_matrix_live_probe_completed": True,
        "single_case_live_probe_completed": False,
        "diagnostic_only_not_readiness": True,
    }
    assert artifact["blockers"] == []


def test_activation_review_manifest_accepts_optional_context_live_gate_without_live_canary() -> None:
    inputs = _valid_inputs()
    inputs["context_live_diagnostic_gate"] = _context_live_gate(live=False)

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["review_checkpoints"]["context_live_diagnostic_gate"] == "gate_ready_without_live_canary"
    assert (
        artifact["remaining_stop_gates"]["context_live_gate_status"]
        == "context_live_gate_ready_without_live_canary"
    )
    assert artifact["context_live_gate_evidence_present"] is True
    assert artifact["upstream_context_live_gate_llm_invoked"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["context_live_diagnostic_stage_summary"]["live_stage"] == "not_invoked"
    assert artifact["context_live_diagnostic_stage_summary"]["diagnostic_only_not_readiness"] is True
    assert artifact["blockers"] == []


def test_activation_review_manifest_summarizes_single_case_context_live_gate() -> None:
    inputs = _valid_inputs()
    gate = _context_live_gate(live=True)
    gate["live_stage"] = "single-case"
    gate["stage_gate_status"] = "context_live_single_case_probe_pass"
    gate["summary"]["live_provider_output_count"] = 1  # type: ignore[index]
    inputs["context_live_diagnostic_gate"] = gate

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["context_live_diagnostic_stage_summary"] == {
        "live_stage": "single-case",
        "stage_gate_status": "context_live_single_case_probe_pass",
        "live_provider_output_count": 1,
        "live_blocked_response_count": 0,
        "full_matrix_live_probe_completed": False,
        "single_case_live_probe_completed": True,
        "diagnostic_only_not_readiness": True,
    }
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["product_readiness_claimed"] is False


def test_activation_review_manifest_blocks_context_live_gate_overclaim_or_ad_hoc_probe() -> None:
    inputs = _valid_inputs()
    gate = _context_live_gate(live=True)
    gate["fooddb_used"] = True
    gate["ad_hoc_live_case_selection_allowed"] = True
    gate["fixed_case_matrix_used"] = False
    gate["summary"]["live_blocked_response_count"] = 1  # type: ignore[index]
    inputs["context_live_diagnostic_gate"] = gate

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_gate.fooddb_used" in artifact["blockers"]
    assert "context_live_diagnostic_gate.ad_hoc_live_case_selection_allowed" in artifact["blockers"]
    assert "context_live_diagnostic_gate.fixed_case_matrix_not_used" in artifact["blockers"]
    assert "context_live_diagnostic_gate.live_blocked_response_count_nonzero" in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_activation_review_manifest_blocks_context_live_gate_missing_child_evidence_paths() -> None:
    inputs = _valid_inputs()
    gate = _context_live_gate(live=True)
    gate["artifact_paths"] = {
        "context_live_diagnostic_case_matrix": "artifacts/case_matrix.json",
        "context_live_diagnostic_canary": "artifacts/canary.json",
    }
    inputs["context_live_diagnostic_gate"] = gate

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert (
        "context_live_diagnostic_gate.artifact_paths."
        "context_live_diagnostic_anti_overfit_guard_missing"
    ) in artifact["blockers"]
    assert (
        "context_live_diagnostic_gate.artifact_paths."
        "context_live_response_contract_dry_run_missing"
    ) in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_activation_review_manifest_blocks_context_live_review_pack_readiness_or_fooddb_overclaim() -> None:
    inputs = _valid_inputs()
    review_pack = _context_live_review_pack(live=True)
    review_pack["product_readiness_claimed"] = True
    review_pack["readiness_claimed"] = True
    review_pack["fooddb_used"] = True
    inputs["context_live_diagnostic_review_pack"] = review_pack

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_review_pack.product_readiness_claimed" in artifact["blockers"]
    assert "context_live_diagnostic_review_pack.readiness_claimed" in artifact["blockers"]
    assert "context_live_diagnostic_review_pack.fooddb_used" in artifact["blockers"]
    assert artifact["product_readiness_claimed"] is False
    assert artifact["ready_for_fdb_integration"] is False


def test_activation_review_manifest_blocks_missing_or_blocked_inputs() -> None:
    inputs = _valid_inputs()
    inputs["pl_ce_browser_activation_evidence_gate"] = {
        "artifact_type": "accurate_intake_pl_ce_browser_activation_evidence_gate",
        "status": "blocked",
        "all_required_browser_artifacts_executed": False,
        "browser_executed_required": True,
    }

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "pl_ce_browser_activation_evidence_gate.unexpected_status:blocked" in artifact["blockers"]
    assert "pl_ce_browser_activation_evidence_gate.browser_artifacts_not_all_executed" in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_activation_review_manifest_blocks_swapped_identity_or_readiness_overclaim() -> None:
    inputs = _valid_inputs()
    inputs["pl_ce_local_mvp_candidate_bundle"]["artifact_type"] = "wrong"
    inputs["pl_ce_browser_activation_evidence_gate"]["ready_for_live_diagnostic_decision"] = True
    inputs["pl_ce_browser_activation_evidence_gate"]["product_readiness_claimed"] = True
    inputs["pl_ce_ui_context_alignment_pack"]["product_readiness_claimed"] = True

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "pl_ce_local_mvp_candidate_bundle.unexpected_artifact_type:wrong" in artifact["blockers"]
    assert "pl_ce_browser_activation_evidence_gate.ready_for_live_diagnostic_decision" in artifact["blockers"]
    assert "pl_ce_browser_activation_evidence_gate.product_readiness_claimed" in artifact["blockers"]
    assert "pl_ce_ui_context_alignment_pack.product_readiness_claimed" in artifact["blockers"]
    assert artifact["product_readiness_claimed"] is False


def test_activation_review_manifest_blocks_thin_or_contradictory_ready_inputs() -> None:
    thin_inputs = {
        "pl_ce_local_mvp_candidate_bundle": {
            "artifact_type": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
            "status": "pl_ce_local_mvp_candidate_ready_for_human_review",
            "activation_gate_status": "blocked_pending_human_and_browser_activation",
        },
        "pl_ce_browser_activation_evidence_gate": {
            "artifact_type": "accurate_intake_pl_ce_browser_activation_evidence_gate",
            "status": "browser_activation_evidence_ready_for_human_review",
            "all_required_browser_artifacts_executed": True,
            "browser_executed_required": True,
            "blockers": ["contradiction_should_block"],
        },
    }

    artifact = build_pl_ce_activation_review_manifest_artifact(thin_inputs)

    assert artifact["status"] == "blocked"
    assert "pl_ce_local_mvp_candidate_bundle.missing_artifact_schema_version" in artifact["blockers"]
    assert "pl_ce_local_mvp_candidate_bundle.required_inputs_incomplete" in artifact["blockers"]
    assert "pl_ce_local_mvp_candidate_bundle.included_artifact_statuses_missing" in artifact["blockers"]
    assert "pl_ce_browser_activation_evidence_gate.upstream_blockers_present" in artifact["blockers"]
    assert "pl_ce_browser_activation_evidence_gate.required_inputs_incomplete" in artifact["blockers"]


def test_activation_review_manifest_blocks_nested_status_or_browser_contradiction() -> None:
    inputs = _valid_inputs()
    inputs["pl_ce_local_mvp_candidate_bundle"]["included_artifact_statuses"][
        "mvp_gate_summary"
    ]["status"] = "blocked"
    inputs["pl_ce_browser_activation_evidence_gate"]["included_artifact_statuses"][
        "product_pages_visual_qa"
    ]["status"] = "fail"
    inputs["pl_ce_browser_activation_evidence_gate"]["included_artifact_statuses"][
        "product_pages_visual_qa"
    ]["browser_executed"] = False
    inputs["pl_ce_ui_context_alignment_pack"]["summary"]["chat_context_reload_checked"] = False
    inputs["pl_ce_ui_context_alignment_pack"]["included_artifact_statuses"][
        "product_pages_short_term_context_smoke"
    ]["browser_executed"] = False

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert (
        "pl_ce_local_mvp_candidate_bundle.included_artifact_statuses.mvp_gate_summary.unexpected_status:blocked"
        in artifact["blockers"]
    )
    assert (
        "pl_ce_browser_activation_evidence_gate.included_artifact_statuses.product_pages_visual_qa.unexpected_status:fail"
        in artifact["blockers"]
    )
    assert (
        "pl_ce_browser_activation_evidence_gate.included_artifact_statuses.product_pages_visual_qa.browser_not_executed"
        in artifact["blockers"]
    )
    assert "pl_ce_ui_context_alignment_pack.chat_context_reload_not_checked" in artifact["blockers"]
    assert (
        "pl_ce_ui_context_alignment_pack.included_artifact_statuses."
        "product_pages_short_term_context_smoke.browser_not_executed"
        in artifact["blockers"]
    )


def test_activation_review_manifest_blocks_missing_ui_context_alignment_pack() -> None:
    inputs = _valid_inputs()
    inputs.pop("pl_ce_ui_context_alignment_pack")

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "pl_ce_ui_context_alignment_pack.unexpected_status:" in artifact["blockers"]
    assert "pl_ce_ui_context_alignment_pack.unexpected_artifact_type:None" in artifact["blockers"]
    assert "pl_ce_ui_context_alignment_pack.required_inputs_incomplete" in artifact["blockers"]


def test_activation_review_manifest_blocks_missing_context_live_dry_run_evaluator() -> None:
    inputs = _valid_inputs()
    inputs.pop("context_live_diagnostic_dry_run_evaluator")

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_dry_run_evaluator.unexpected_status:" in artifact["blockers"]
    assert (
        "context_live_diagnostic_dry_run_evaluator.unexpected_artifact_type:None"
        in artifact["blockers"]
    )
    assert (
        artifact["remaining_stop_gates"]["context_live_dry_run_status"]
        == "blocked_before_live_diagnostic"
    )
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_activation_review_manifest_blocks_missing_context_live_holdout_plan() -> None:
    inputs = _valid_inputs()
    inputs.pop("context_live_diagnostic_holdout_plan")

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_holdout_plan.unexpected_status:" in artifact["blockers"]
    assert (
        "context_live_diagnostic_holdout_plan.unexpected_artifact_type:None"
        in artifact["blockers"]
    )
    assert (
        artifact["remaining_stop_gates"]["context_live_holdout_plan_status"]
        == "blocked_before_live_diagnostic"
    )
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_activation_review_manifest_blocks_missing_context_live_response_contract_dry_run() -> None:
    inputs = _valid_inputs()
    inputs.pop("context_live_response_contract_dry_run")

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_response_contract_dry_run.unexpected_status:" in artifact["blockers"]
    assert (
        "context_live_response_contract_dry_run.unexpected_artifact_type:None"
        in artifact["blockers"]
    )
    assert (
        artifact["remaining_stop_gates"]["context_live_response_contract_status"]
        == "blocked_before_live_diagnostic"
    )
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_activation_review_manifest_blocks_context_live_dry_run_evaluator_blocked_status() -> None:
    inputs = _valid_inputs()
    inputs["context_live_diagnostic_dry_run_evaluator"]["status"] = "blocked"
    inputs["context_live_diagnostic_dry_run_evaluator"]["blockers"] = ["fixture_output_missing"]

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_dry_run_evaluator.unexpected_status:blocked" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.upstream_blockers_present" in artifact["blockers"]
    assert artifact["review_checkpoints"]["context_live_diagnostic_dry_run_evaluator"] == "blocked_or_missing"


def test_activation_review_manifest_blocks_context_live_response_contract_dry_run_status() -> None:
    inputs = _valid_inputs()
    inputs["context_live_response_contract_dry_run"]["status"] = "blocked"
    inputs["context_live_response_contract_dry_run"]["blockers"] = ["fixture_response_contract_gap"]

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_response_contract_dry_run.unexpected_status:blocked" in artifact["blockers"]
    assert "context_live_response_contract_dry_run.upstream_blockers_present" in artifact["blockers"]
    assert artifact["review_checkpoints"]["context_live_response_contract_dry_run"] == "blocked_or_missing"


def test_activation_review_manifest_blocks_context_live_dry_run_overclaims() -> None:
    inputs = _valid_inputs()
    dry_run = inputs["context_live_diagnostic_dry_run_evaluator"]
    dry_run["live_provider_invoked"] = True
    dry_run["fooddb_used"] = True
    dry_run["manager_context_packet_schema_changed"] = True
    dry_run["deterministic_selected_intent"] = True

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_dry_run_evaluator.live_provider_invoked" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.fooddb_used" in artifact["blockers"]
    assert (
        "context_live_diagnostic_dry_run_evaluator.manager_context_packet_schema_changed"
        in artifact["blockers"]
    )
    assert (
        "context_live_diagnostic_dry_run_evaluator.deterministic_selected_intent"
        in artifact["blockers"]
    )
    assert artifact["live_provider_called"] is False
    assert artifact["fooddb_evidence_used"] is False


def test_activation_review_manifest_blocks_context_live_holdout_plan_overclaims() -> None:
    inputs = _valid_inputs()
    holdout = inputs["context_live_diagnostic_holdout_plan"]
    holdout["live_provider_invoked"] = True
    holdout["fooddb_used"] = True
    holdout["provider_optimized_case_selection_allowed"] = True
    holdout["deterministic_role"] = "select_intent"

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_holdout_plan.live_provider_invoked" in artifact["blockers"]
    assert "context_live_diagnostic_holdout_plan.fooddb_used" in artifact["blockers"]
    assert (
        "context_live_diagnostic_holdout_plan.provider_optimized_case_selection_allowed_not_false"
        in artifact["blockers"]
    )
    assert "context_live_diagnostic_holdout_plan.deterministic_role_wrong" in artifact["blockers"]
    assert artifact["live_provider_called"] is False
    assert artifact["fooddb_evidence_used"] is False


def test_activation_review_manifest_blocks_context_live_response_contract_overclaims() -> None:
    inputs = _valid_inputs()
    dry_run = inputs["context_live_response_contract_dry_run"]
    dry_run["provider_call_ready"] = True
    dry_run["live_provider_invoked"] = True
    dry_run["fooddb_used"] = True
    dry_run["deterministic_selected_target"] = True

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_response_contract_dry_run.provider_call_ready" in artifact["blockers"]
    assert "context_live_response_contract_dry_run.live_provider_invoked" in artifact["blockers"]
    assert "context_live_response_contract_dry_run.fooddb_used" in artifact["blockers"]
    assert (
        "context_live_response_contract_dry_run.deterministic_selected_target"
        in artifact["blockers"]
    )
    assert artifact["live_provider_called"] is False
    assert artifact["fooddb_evidence_used"] is False


def test_activation_review_manifest_blocks_weak_context_live_dry_run_summary() -> None:
    inputs = _valid_inputs()
    dry_run = inputs["context_live_diagnostic_dry_run_evaluator"]
    dry_run["fixed_case_matrix_used"] = False
    dry_run["summary"] = {
        "case_count": len(REQUIRED_CASE_IDS) - 1,
        "evaluated_case_count": len(REQUIRED_CASE_IDS) - 1,
        "blocked_case_count": 1,
        "target_candidate_cases": 0,
        "pending_pin_cases": 0,
        "ambiguity_cases": 0,
    }

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_dry_run_evaluator.fixed_case_matrix_not_used" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.case_count_mismatch" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.evaluated_case_count_mismatch" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.blocked_case_count_nonzero" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.target_candidate_cases_missing" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.pending_pin_cases_missing" in artifact["blockers"]
    assert "context_live_diagnostic_dry_run_evaluator.ambiguity_cases_missing" in artifact["blockers"]


def test_activation_review_manifest_blocks_weak_context_live_holdout_plan_summary() -> None:
    inputs = _valid_inputs()
    holdout = inputs["context_live_diagnostic_holdout_plan"]
    holdout["fixed_case_matrix_used"] = False
    holdout["summary"] = {
        "case_count": len(REQUIRED_CASE_IDS) - 1,
        "withheld_holdout_variant_count": 1,
        "cases_with_holdouts": 1,
        "compound_cases": 0,
        "ambiguity_cases": 0,
        "pending_pin_cases": 0,
        "target_candidate_cases": 0,
    }

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_holdout_plan.fixed_case_matrix_used_not_true" in artifact[
        "blockers"
    ]
    assert "context_live_diagnostic_holdout_plan.case_count_mismatch" in artifact["blockers"]
    assert "context_live_diagnostic_holdout_plan.withheld_holdout_count_too_low" in artifact[
        "blockers"
    ]
    assert "context_live_diagnostic_holdout_plan.cases_with_holdouts_mismatch" in artifact[
        "blockers"
    ]
    assert "context_live_diagnostic_holdout_plan.compound_cases_missing" in artifact["blockers"]


def test_activation_review_manifest_blocks_weak_context_live_response_contract_summary() -> None:
    inputs = _valid_inputs()
    dry_run = inputs["context_live_response_contract_dry_run"]
    dry_run["full_matrix_required"] = False
    dry_run["summary"] = {
        "case_count": len(REQUIRED_CASE_IDS) - 1,
        "validated_response_count": len(REQUIRED_CASE_IDS) - 1,
        "blocked_response_count": 1,
        "target_candidate_response_count": 0,
        "ambiguity_preserved_response_count": 0,
    }

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_response_contract_dry_run.full_matrix_not_required" in artifact["blockers"]
    assert "context_live_response_contract_dry_run.case_count_mismatch" in artifact["blockers"]
    assert (
        "context_live_response_contract_dry_run.validated_response_count_mismatch"
        in artifact["blockers"]
    )
    assert (
        "context_live_response_contract_dry_run.blocked_response_count_nonzero"
        in artifact["blockers"]
    )
    assert (
        "context_live_response_contract_dry_run.target_candidate_response_missing"
        in artifact["blockers"]
    )
    assert (
        "context_live_response_contract_dry_run.ambiguity_response_missing"
        in artifact["blockers"]
    )


def test_activation_review_manifest_blocks_undercovered_ui_context_pack() -> None:
    inputs = _valid_inputs()
    inputs["pl_ce_ui_context_alignment_pack"]["summary"]["context_covered_capabilities"] = 1

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "pl_ce_ui_context_alignment_pack.context_capabilities_not_covered" in artifact["blockers"]


def test_activation_review_manifest_blocks_invalid_renderer_source_map_gate() -> None:
    inputs = _valid_inputs()
    inputs["pl_ce_ui_context_alignment_pack"]["included_artifact_statuses"][
        "product_pages_renderer_source_map"
    ]["status"] = "blocked"
    inputs["pl_ce_ui_context_alignment_pack"]["summary"]["renderer_source_map_page_count"] = 0
    inputs["pl_ce_ui_context_alignment_pack"]["summary"]["renderer_source_map_selector_count"] = 0
    inputs["pl_ce_ui_context_alignment_pack"]["summary"]["renderer_source_map_endpoint_count"] = 0

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert (
        "pl_ce_ui_context_alignment_pack.included_artifact_statuses."
        "product_pages_renderer_source_map.unexpected_status:blocked"
        in artifact["blockers"]
    )
    assert (
        "pl_ce_ui_context_alignment_pack.renderer_source_map_page_count_mismatch"
        in artifact["blockers"]
    )
    assert (
        "pl_ce_ui_context_alignment_pack.renderer_source_map_selector_count_too_low"
        in artifact["blockers"]
    )
    assert (
        "pl_ce_ui_context_alignment_pack.renderer_source_map_endpoint_count_too_low"
        in artifact["blockers"]
    )


def test_activation_review_manifest_accepts_context_matrix_known_runtime_gap_status() -> None:
    inputs = _valid_inputs()
    inputs["pl_ce_local_mvp_candidate_bundle"]["included_artifact_statuses"][
        "context_coverage_matrix"
    ]["status"] = "context_coverage_matrix_ready_with_known_runtime_gaps"

    artifact = build_pl_ce_activation_review_manifest_artifact(inputs)

    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["blockers"] == []


def test_activation_review_manifest_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_activation_review_manifest import main

    output_path = tmp_path / "activation-review-manifest.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])
    gate_path = tmp_path / "context_live_diagnostic_gate.json"
    gate_path.write_text(json.dumps(_context_live_gate(live=False), ensure_ascii=False), encoding="utf-8")
    args.extend(["--artifact", f"context_live_diagnostic_gate={gate_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["included_artifact_statuses"]["pl_ce_local_mvp_candidate_bundle"]["source_artifact_path"]


def test_activation_review_manifest_cli_accepts_optional_context_live_review_pack(
    tmp_path: Path,
) -> None:
    from scripts.build_accurate_intake_pl_ce_activation_review_manifest import main

    output_path = tmp_path / "activation-review-manifest.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])
    gate_path = tmp_path / "context_live_diagnostic_gate.json"
    gate_path.write_text(json.dumps(_context_live_gate(live=False), ensure_ascii=False), encoding="utf-8")
    args.extend(["--artifact", f"context_live_diagnostic_gate={gate_path}"])
    review_pack_path = tmp_path / "context_live_diagnostic_review_pack.json"
    review_pack_path.write_text(
        json.dumps(_context_live_review_pack(live=True), ensure_ascii=False),
        encoding="utf-8",
    )
    args.extend(["--artifact", f"context_live_diagnostic_review_pack={review_pack_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["review_checkpoints"]["context_live_diagnostic_review_pack"] == "live_canary_passed"
    assert artifact["upstream_live_llm_invoked"] is True


def test_activation_review_manifest_cli_accepts_optional_context_live_gate(
    tmp_path: Path,
) -> None:
    from scripts.build_accurate_intake_pl_ce_activation_review_manifest import main

    output_path = tmp_path / "activation-review-manifest.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])
    gate_path = tmp_path / "context_live_diagnostic_gate.json"
    gate_path.write_text(
        json.dumps(_context_live_gate(live=True), ensure_ascii=False),
        encoding="utf-8",
    )
    args.extend(["--artifact", f"context_live_diagnostic_gate={gate_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "pl_ce_activation_review_manifest_ready"
    assert artifact["review_checkpoints"]["context_live_diagnostic_gate"] == "gate_live_canary_passed"
    assert artifact["upstream_context_live_gate_llm_invoked"] is True


def test_activation_review_manifest_cli_rejects_unknown_artifact_group(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.build_accurate_intake_pl_ce_activation_review_manifest import main

    output_path = tmp_path / "activation-review-manifest.json"
    exit_code = main(
        [
            "--artifact",
            f"pl_ce_browser_activation_typo={tmp_path / 'activation.json'}",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert printed["status"] == "invalid_arguments"
    assert printed["unknown_artifact_groups"] == ["pl_ce_browser_activation_typo"]
    assert not output_path.exists()


def test_activation_review_manifest_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_activation_manifest_contract.py"),
        Path("app/composition/accurate_intake_pl_ce_activation_manifest_group_checks.py"),
        Path("app/composition/accurate_intake_pl_ce_activation_manifest_validation.py"),
        Path("app/composition/accurate_intake_pl_ce_activation_review_manifest.py"),
        Path("app/composition/accurate_intake_context_live_diagnostic_holdout_plan.py"),
        Path("scripts/build_accurate_intake_context_live_diagnostic_holdout_plan.py"),
        Path("scripts/build_accurate_intake_pl_ce_activation_review_manifest.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "from tavily",
        "import tavily",
        "tavilyclient",
        "tavilysearch",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
        "fooddb_evidence_used = True",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
    ]
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8").lower()
    ci_activation_segment = workflow[
        workflow.index("run product pages browser e2e diagnostic") : workflow.index(
            "upload product pages browser e2e report"
        )
    ]
    combined_source = (
        "\n".join(path.read_text(encoding="utf-8").lower() for path in source_paths)
        + "\n"
        + ci_activation_segment
    )

    for fragment in forbidden:
        assert fragment.lower() not in combined_source


def test_ci_builds_activation_review_manifest() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_pl_ce_activation_review_manifest.py" in workflow
    assert "build_accurate_intake_context_live_diagnostic_dry_run_evaluator.py" in workflow
    assert "build_accurate_intake_context_live_diagnostic_holdout_plan.py" in workflow
    assert "build_accurate_intake_context_live_response_contract_dry_run.py" in workflow
    assert "run_accurate_intake_context_live_diagnostic_gate.py" in workflow
    assert "build_accurate_intake_pl_ce_activation_review_manifest.py" in workflow
    assert "pl_ce_ui_context_alignment_pack=artifacts/accurate_intake_pl_ce_ui_context_alignment_pack_ci.json" in workflow
    assert (
        "context_live_diagnostic_dry_run_evaluator="
        "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json"
    ) in workflow
    assert (
        "context_live_diagnostic_holdout_plan="
        "artifacts/accurate_intake_context_live_diagnostic_holdout_plan_ci.json"
    ) in workflow
    assert (
        "context_live_response_contract_dry_run="
        "artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json"
    ) in workflow
    assert (
        "context_live_diagnostic_gate="
        "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json"
    ) in workflow
    assert "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json" in workflow
    assert "accurate_intake_pl_ce_activation_review_manifest_ci.json" in workflow
