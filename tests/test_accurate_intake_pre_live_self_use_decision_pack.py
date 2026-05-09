from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG,
)
from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (
    REQUIRED_PRE_LIVE_EVIDENCE,
    build_pre_live_self_use_decision_pack,
)

_REMOVED_FIXED_FALSE_OUTPUT_FIELDS = (
    "ready_for_live_diagnostic_decision",
    "private_self_use_approved",
)


def _assert_removed_fixed_false_outputs(pack: dict) -> None:
    for field in _REMOVED_FIXED_FALSE_OUTPUT_FIELDS:
        assert field not in pack


def _evidence(**overrides: dict) -> dict:
    evidence = {
        "phase_c_gate": {"status": "pass"},
        "accurate_intake_mvp_gate": {"status": "pass"},
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "chat_history_reload_gate": {"status": "pass"},
        "free_text_manual_target_gate": {"status": "pass"},
        "dogfood_review_queue": {"status": "generated"},
        "local_dogfood_data_hygiene": {"status": "pass"},
        "local_operator_data_hygiene_bundle": {
            "status": "local_operator_data_hygiene_ready",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: {
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
            "status": "product_pages_self_use_flow_ready_for_human_review",
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "three_distinct_pages_verified": True,
                "seven_day_diary_checked": True,
                "short_term_context_checked": True,
                "target_candidate_ui_checked": True,
                "body_observation_same_truth_checked": True,
            },
        },
        "ui_context_alignment_pack": {
            "status": "ui_context_alignment_ready_for_human_review",
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "chat_context_reload_checked": True,
                "seven_day_diary_checked": True,
                "body_read_model_checked": True,
            },
        },
        "browser_activation_evidence_gate": {
            "status": "browser_activation_evidence_ready_for_human_review",
            "all_required_browser_artifacts_executed": True,
            "browser_executed_required": True,
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {"body_observation_same_truth_checked": True},
        },
        "manager_tool_surface_inventory": {
            "status": "manager_tool_surface_inventory_ready_for_human_review",
            "required_direct_lane_ids": [f"lane-{index}" for index in range(7)],
            "required_manager_tools": [f"tool-{index}" for index in range(10)],
            "summary": {
                "direct_lane_count": 7,
                "target_tool_count": 10,
                "mutation_bearing_lane_count": 4,
                "read_only_tool_count": 6,
            },
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "non_fooddb_manager_tool_contract": {
            "status": "non_fooddb_manager_tool_contract_ready_for_human_review",
            "summary": {
                "inventory_backed_tool_count": 10,
                "read_only_tool_count": 7,
                "proposal_tool_count": 1,
                "mutation_tool_count": 3,
                "legacy_direct_route_debt_count": 1,
                "direct_lane_bridge_count": 7,
            },
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "manager_tool_choice_regression_wall": {
            "status": "manager_tool_choice_regression_wall_pass",
            "semantic_owner": "fixture_manager_structured_decision",
            "deterministic_selected_tool": False,
            "deterministic_selected_intent": False,
            "frontend_raw_text_semantic_router": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {"case_count": 11},
        },
        "context_conditioned_intent_wall": {
            "status": "pass",
            "manager_fixture_semantic_source_used": True,
            "pending_followup_carryover": True,
            "ambiguity_preserved": True,
            "query_no_mutation": True,
            "target_update_requires_manager_decision": True,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "frontend_raw_text_semantic_router": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
            "runtime_truth_changed": False,
            "fooddb_truth_updated": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {"scenario_count": 11},
        },
        "non_fooddb_read_only_tool_loop_fake_smoke": {
            "status": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
            "semantic_owner": "fixture_manager_structured_decision",
            "tool_execution_owner": "deterministic_domain_read_model_fixture",
            "deterministic_selected_tool": False,
            "deterministic_selected_intent": False,
            "frontend_raw_text_semantic_router": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {"case_count": 6},
        },
        "non_fooddb_mutation_tool_guard_smoke": {
            "status": "non_fooddb_mutation_tool_guard_smoke_pass",
            "semantic_owner": "fixture_manager_structured_decision",
            "deterministic_selected_tool": False,
            "deterministic_selected_intent": False,
            "frontend_raw_text_semantic_router": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {"case_count": 10},
        },
        "manager_intent_readiness_review_pack": {
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
            "status": "pass",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "live_provider_approved": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "case_count": 11,
                "compound_cases": 1,
            },
        },
        "context_live_diagnostic_anti_overfit_guard": {
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
            "status": "pass",
            "plan_only": True,
            "fixture_only": True,
            "fixed_case_matrix_used": True,
            "holdout_variants_withheld_from_default_live_prompt": True,
            "ad_hoc_live_case_selection_allowed": False,
            "provider_optimized_case_selection_allowed": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "case_count": 11,
                "withheld_holdout_variant_count": 22,
                "cases_with_holdouts": 11,
                "compound_cases": 1,
                "ambiguity_cases": 1,
            },
        },
        "context_live_provider_input_preflight": {
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
            "status": "context_live_diagnostic_gate_ready_without_live_canary",
            "review_pack_status": "context_live_diagnostic_review_ready_without_live_canary",
            "canary_status": "blocked",
            "live_provider_allowed": False,
            "live_provider_required": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
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
            "summary": {
                "fixed_case_count": 11,
                "dry_run_validated_response_count": 11,
                "live_provider_output_count": 0,
                "live_blocked_response_count": 0,
            },
        },
    }
    evidence.update(overrides)
    return evidence


def test_pre_live_decision_pack_lists_required_evidence_without_approving_live() -> None:
    pack = build_pre_live_self_use_decision_pack(_evidence())

    assert pack["artifact_type"] == "accurate_intake_pre_live_self_use_decision_pack"
    assert pack["status"] == "generated"
    assert pack["claim_scope"] == "pre_live_local_web_self_use_decision_pack"
    assert pack["required_evidence"] == list(REQUIRED_PRE_LIVE_EVIDENCE)
    assert pack["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert pack["missing_evidence"] == []
    assert "live_llm_invoked" not in pack
    assert "web_tavily_invoked" not in pack
    assert "live_canary_approved" not in pack
    assert "kimi_active_runtime_default_allowed" not in pack
    assert "product_readiness_claimed" not in pack
    assert "runtime_web_activation_approved" not in pack
    assert "production_db_ready_claimed" not in pack
    _assert_removed_fixed_false_outputs(pack)
    assert pack["blockers"] == []
    assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is True
    assert "ready_for_pl_ce_local_review" not in pack
    assert pack["capability_axis_summary"] == {
        "browser_execution": {
            "status": "pass",
            "browser_executed": True,
        },
        "current_shell_compatibility_local_review": {
            "status": "ready_for_human_review",
            CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG: True,
        },
        "manager_intent_readiness": {
            "status": "ready_for_human_review",
            "semantic_owner": "fixture_manager_structured_decision",
            "context_known_runtime_gaps": 0,
        },
        "context_live_diagnostic": {
            "status": "pre_live_ready_without_live_canary",
            "live_stage": "not_invoked",
            "live_provider_output_count": 0,
            "live_blocked_response_count": 0,
            "anti_overfit_guard": "pass",
            "holdout_plan": "pass",
            "response_contract_dry_run": "pass",
        },
        "fooddb_dependency": {
            "status": "blocked_out_of_scope_waiting_fooddb_artifact",
            "ready_for_fdb_integration": False,
        },
        "final_e2e_dependency": {
            "status": "blocked_until_fooddb_and_live_manager_integration",
            "selected_option": "ready_for_human_limited_live_canary_decision",
        },
    }


def test_pre_live_decision_pack_accepts_legacy_local_review_group_alias() -> None:
    evidence = _evidence()
    del evidence[CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID]
    evidence["pl_ce_local_review_decision_pack"] = {
        "status": "ready_for_human_pl_ce_review",
        "shared_contract_changed": False,
        "ready_for_live_diagnostic_decision": False,
        "ready_for_fdb_integration": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "real_fooddb_pass_claimed": False,
        "private_self_use_approved": False,
    }

    pack = build_pre_live_self_use_decision_pack(evidence)

    assert pack["missing_evidence"] == []
    assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is True
    assert "ready_for_pl_ce_local_review" not in pack


def test_pre_live_decision_pack_stays_local_when_review_or_data_hygiene_evidence_missing() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            dogfood_review_queue={"status": "missing"},
            local_dogfood_data_hygiene={"status": "blocked"},
            local_operator_data_hygiene_bundle={},
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "live_canary_approved" not in pack
    assert pack["missing_evidence"] == [
        "dogfood_review_queue",
        "local_dogfood_data_hygiene",
        "local_operator_data_hygiene_bundle",
    ]


def test_pre_live_decision_pack_requires_product_pages_and_non_fooddb_manager_tool_evidence() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            browser_activation_evidence_gate={},
            manager_tool_surface_inventory={},
            non_fooddb_manager_tool_contract={},
            non_fooddb_mutation_tool_guard_smoke={},
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "browser_activation_evidence_gate" in pack["missing_evidence"]
    assert "manager_tool_surface_inventory" in pack["missing_evidence"]
    assert "non_fooddb_manager_tool_contract" in pack["missing_evidence"]
    assert "non_fooddb_mutation_tool_guard_smoke" in pack["missing_evidence"]


def test_pre_live_decision_pack_blocks_non_fooddb_manager_tool_and_browser_overclaims() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            browser_activation_evidence_gate={
                "status": "browser_activation_evidence_ready_for_human_review",
                "all_required_browser_artifacts_executed": False,
                "browser_executed_required": False,
                "product_readiness_claimed": True,
            },
            non_fooddb_manager_tool_contract={
                "status": "non_fooddb_manager_tool_contract_ready_for_human_review",
                "summary": {
                    "inventory_backed_tool_count": 2,
                    "read_only_tool_count": 1,
                    "proposal_tool_count": 0,
                    "mutation_tool_count": 1,
                    "legacy_direct_route_debt_count": 0,
                    "direct_lane_bridge_count": 1,
                },
            },
            manager_tool_choice_regression_wall={
                "status": "manager_tool_choice_regression_wall_pass",
                "semantic_owner": "not_fixture_manager",
                "summary": {"case_count": 3},
            },
            non_fooddb_read_only_tool_loop_fake_smoke={
                "status": "non_fooddb_read_only_tool_loop_fake_smoke_pass",
                "summary": {"case_count": 2},
                "live_llm_invoked": True,
            },
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "browser_activation_evidence_gate_browser_artifacts_not_all_executed" in pack["blockers"]
    assert "browser_activation_evidence_gate_browser_execution_not_required" in pack["blockers"]
    assert "browser_activation_evidence_gate_product_readiness_claimed" in pack["blockers"]
    assert "non_fooddb_manager_tool_contract_inventory_backed_tool_count_too_low" in pack["blockers"]
    assert "non_fooddb_manager_tool_contract_read_only_tool_count_too_low" in pack["blockers"]
    assert "non_fooddb_manager_tool_contract_direct_lane_bridge_count_too_low" in pack["blockers"]
    assert "manager_tool_choice_regression_wall_semantic_owner_not_fixture_manager" in pack["blockers"]
    assert "manager_tool_choice_regression_wall_case_count_too_low" in pack["blockers"]
    assert "non_fooddb_read_only_tool_loop_fake_smoke_case_count_too_low" in pack["blockers"]
    assert "non_fooddb_read_only_tool_loop_fake_smoke_live_llm_invoked" in pack["blockers"]


def test_pre_live_decision_pack_blocks_stale_body_same_truth_summaries() -> None:
    for group_id, blocker in (
        (
            "product_pages_self_use_flow_gate",
            "product_pages_self_use_flow_gate_body_observation_same_truth_not_checked",
        ),
        (
            "browser_activation_evidence_gate",
            "browser_activation_evidence_gate_body_observation_same_truth_not_checked",
        ),
    ):
        evidence = _evidence()
        evidence[group_id]["summary"]["body_observation_same_truth_checked"] = False

        pack = build_pre_live_self_use_decision_pack(evidence)

        assert pack["selected_option"] == "stay_local_self_use"
        assert blocker in pack["blockers"]


def test_pre_live_decision_pack_blocks_manager_tool_inventory_without_surface_proof() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            manager_tool_surface_inventory={
                "status": "manager_tool_surface_inventory_ready_for_human_review",
                "summary": {"direct_lane_count": 1, "target_tool_count": 2},
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "manager_tool_surface_inventory_required_direct_lane_count_too_low" in pack["blockers"]
    assert "manager_tool_surface_inventory_required_manager_tool_count_too_low" in pack["blockers"]
    assert "manager_tool_surface_inventory_direct_lane_count_too_low" in pack["blockers"]
    assert "manager_tool_surface_inventory_target_tool_count_too_low" in pack["blockers"]


def test_pre_live_decision_pack_blocks_unsafe_operator_data_hygiene_flags() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            local_operator_data_hygiene_bundle={
                "status": "local_operator_data_hygiene_ready",
                "writes_performed": True,
                "import_allowed": True,
                "production_db_used": True,
                "fooddb_truth_updated": True,
            },
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "local_operator_data_hygiene_bundle_writes_performed" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_import_allowed" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_production_db_used" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_fooddb_truth_updated" in pack["blockers"]
    assert "live_canary_approved" not in pack


def test_pre_live_decision_pack_requires_browser_executed_evidence_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(browser_shell_smoke={"status": "blocked", "browser_executed": False})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "browser_shell_smoke" in pack["missing_evidence"]
    assert pack["evidence_status"]["browser_shell_smoke"]["browser_executed"] is False
    assert pack["capability_axis_summary"]["browser_execution"] == {
        "status": "blocked_or_missing",
        "browser_executed": False,
    }
    assert (
        pack["capability_axis_summary"]["final_e2e_dependency"]["selected_option"]
        == "stay_local_self_use"
    )


def test_pre_live_decision_pack_requires_pl_ce_local_review_gate_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(**{CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: {}})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID in pack["missing_evidence"]
    assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is False
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_requires_context_live_case_matrix_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_case_matrix={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_case_matrix" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_requires_manager_intent_readiness_pack() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(manager_intent_readiness_review_pack={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "manager_intent_readiness_review_pack" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_blocks_manager_intent_readiness_overclaims() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            manager_intent_readiness_review_pack={
                "status": "manager_intent_readiness_ready_for_human_review",
                "review_required_before_provider_call": True,
                "semantic_owner": "fixture_manager_structured_decision",
                "ready_for_live_diagnostic_decision": True,
                "live_llm_invoked": True,
                "fooddb_evidence_used": True,
                "mutation_changed": True,
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
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "manager_intent_readiness_review_pack_ready_for_live_diagnostic_decision" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_live_llm_invoked" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_fooddb_evidence_used" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_mutation_changed" in pack["blockers"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_blocks_manager_intent_readiness_weak_coverage() -> None:
    evidence = _evidence()
    evidence["manager_intent_readiness_review_pack"]["summary"] = {
        "intent_wall_scenarios": 10,
        "contextual_interactions": 10,
        "fake_provider_handoff_scenarios": 5,
        "responder_allowed_fact_scenarios": 4,
        "context_covered_capabilities": 8,
        "context_blocked_capabilities": 1,
        "context_known_runtime_gaps": 1,
        "session_pending_followup_carryover_checked": False,
        "session_target_candidate_ui_checked": False,
        "session_long_context_checked": False,
    }

    pack = build_pre_live_self_use_decision_pack(evidence)

    assert pack["selected_option"] == "stay_local_self_use"
    assert "manager_intent_readiness_review_pack_intent_wall_scenarios_too_low" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_contextual_interactions_too_low" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_fake_provider_handoffs_too_low" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_responder_scenarios_too_low" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_context_capabilities_too_low" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_context_blocked_capabilities_present" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_context_known_runtime_gaps_present" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_pending_followup_not_checked" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_target_candidate_ui_not_checked" in pack["blockers"]
    assert "manager_intent_readiness_review_pack_long_context_not_checked" in pack["blockers"]


def test_pre_live_decision_pack_requires_context_live_anti_overfit_guard() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_anti_overfit_guard={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_anti_overfit_guard" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_requires_context_live_holdout_plan() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_holdout_plan={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_holdout_plan" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_requires_context_live_provider_input_preflight() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_provider_input_preflight={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_provider_input_preflight" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_requires_context_live_response_contract_dry_run() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_response_contract_dry_run={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_response_contract_dry_run" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_requires_context_live_diagnostic_gate() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_gate={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_gate" in pack["missing_evidence"]
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_blocks_live_context_gate_or_weak_child_evidence() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_diagnostic_gate={
                "status": "context_live_diagnostic_gate_ready_with_live_canary",
                "review_pack_status": "context_live_diagnostic_review_ready_with_live_canary",
                "live_provider_allowed": True,
                "live_llm_invoked": True,
                "live_provider_invoked": True,
                "fixed_case_matrix_used": False,
                "ad_hoc_live_case_selection_allowed": True,
                "anti_overfit_guard_required": False,
                "response_contract_dry_run_required": False,
                "fooddb_used": True,
                "web_tavily_used": True,
                "mutation_changed": True,
                "manager_context_packet_schema_changed": True,
                "summary": {
                    "fixed_case_count": 1,
                    "dry_run_validated_response_count": 1,
                    "live_blocked_response_count": 1,
                },
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_gate" in pack["missing_evidence"]
    assert "context_live_diagnostic_gate_live_llm_invoked" in pack["blockers"]
    assert "context_live_diagnostic_gate_live_provider_invoked" in pack["blockers"]
    assert "context_live_diagnostic_gate_fooddb_used" in pack["blockers"]
    assert "context_live_diagnostic_gate_web_tavily_used" in pack["blockers"]
    assert "context_live_diagnostic_gate_mutation_changed" in pack["blockers"]
    assert "context_live_diagnostic_gate_manager_context_packet_schema_changed" in pack["blockers"]
    assert "context_live_diagnostic_gate_live_provider_allowed" in pack["blockers"]
    assert "context_live_diagnostic_gate_fixed_case_matrix_missing" in pack["blockers"]
    assert "context_live_diagnostic_gate_ad_hoc_live_case_selection_allowed" in pack["blockers"]
    assert "context_live_diagnostic_gate_anti_overfit_guard_missing" in pack["blockers"]
    assert "context_live_diagnostic_gate_response_contract_dry_run_missing" in pack["blockers"]
    assert "context_live_diagnostic_gate_fixed_case_count_too_low" in pack["blockers"]
    assert "context_live_diagnostic_gate_dry_run_validated_count_too_low" in pack["blockers"]
    assert "context_live_diagnostic_gate_live_blocked_response_count_nonzero" in pack["blockers"]


def test_pre_live_decision_pack_blocks_unsafe_context_live_provider_input_preflight() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_provider_input_preflight={
                "status": "pass",
                "plan_only": False,
                "fixture_only": False,
                "provider_call_ready": True,
                "human_approval_required_before_live_provider": False,
                "fixed_case_matrix_used": False,
                "response_schema_strict": False,
                "deterministic_selected_intent": True,
                "raw_text_intent_router_used": True,
                "live_provider_invoked": True,
                "fooddb_used": True,
                "manager_context_packet_schema_changed": True,
                "summary": {
                    "case_count": 1,
                    "blocked_input_count": 1,
                    "strict_schema_input_count": 1,
                    "target_candidate_inputs": 0,
                    "pending_pin_inputs": 0,
                },
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_provider_input_preflight" in pack["missing_evidence"]
    assert "context_live_provider_input_preflight_live_provider_invoked" in pack["blockers"]
    assert "context_live_provider_input_preflight_fooddb_used" in pack["blockers"]
    assert (
        "context_live_provider_input_preflight_manager_context_packet_schema_changed"
        in pack["blockers"]
    )
    assert "context_live_provider_input_preflight_provider_call_ready" in pack["blockers"]
    assert "context_live_provider_input_preflight_fixed_case_matrix_missing" in pack["blockers"]
    assert "context_live_provider_input_preflight_response_schema_not_strict" in pack["blockers"]
    assert "context_live_provider_input_preflight_deterministic_selected_intent" in pack["blockers"]
    assert "context_live_provider_input_preflight_raw_text_intent_router_used" in pack["blockers"]
    assert "context_live_provider_input_preflight_case_count_too_low" in pack["blockers"]
    assert "context_live_provider_input_preflight_blocked_input_count_nonzero" in pack["blockers"]
    assert "context_live_provider_input_preflight_strict_schema_count_too_low" in pack["blockers"]
    assert "context_live_provider_input_preflight_target_candidate_inputs_missing" in pack["blockers"]
    assert "context_live_provider_input_preflight_pending_pin_inputs_missing" in pack["blockers"]


def test_pre_live_decision_pack_blocks_unsafe_context_live_response_contract_dry_run() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_response_contract_dry_run={
                "status": "pass",
                "plan_only": False,
                "fixture_only": False,
                "provider_call_ready": True,
                "human_approval_required_before_live_provider": False,
                "response_schema_strict": False,
                "deterministic_selected_intent": True,
                "raw_text_intent_router_used": True,
                "live_provider_invoked": True,
                "fooddb_used": True,
                "manager_context_packet_schema_changed": True,
                "mutation_changed": True,
                "summary": {
                    "case_count": 1,
                    "validated_response_count": 1,
                    "blocked_response_count": 1,
                    "target_candidate_response_count": 0,
                    "ambiguity_preserved_response_count": 0,
                    "mutation_request_count": 1,
                },
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_response_contract_dry_run" in pack["missing_evidence"]
    assert "context_live_response_contract_dry_run_live_provider_invoked" in pack["blockers"]
    assert "context_live_response_contract_dry_run_fooddb_used" in pack["blockers"]
    assert "context_live_response_contract_dry_run_manager_context_packet_schema_changed" in pack[
        "blockers"
    ]
    assert "context_live_response_contract_dry_run_mutation_changed" in pack["blockers"]
    assert "context_live_response_contract_dry_run_provider_call_ready" in pack["blockers"]
    assert "context_live_response_contract_dry_run_response_schema_not_strict" in pack["blockers"]
    assert "context_live_response_contract_dry_run_deterministic_selected_intent" in pack["blockers"]
    assert "context_live_response_contract_dry_run_raw_text_intent_router_used" in pack["blockers"]
    assert "context_live_response_contract_dry_run_case_count_too_low" in pack["blockers"]
    assert "context_live_response_contract_dry_run_blocked_response_count_nonzero" in pack["blockers"]
    assert "context_live_response_contract_dry_run_validated_response_count_too_low" in pack["blockers"]
    assert "context_live_response_contract_dry_run_target_candidate_response_missing" in pack["blockers"]
    assert "context_live_response_contract_dry_run_ambiguity_response_missing" in pack["blockers"]
    assert "context_live_response_contract_dry_run_mutation_request_count_nonzero" in pack["blockers"]


def test_pre_live_decision_pack_blocks_unsafe_context_live_anti_overfit_guard() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_diagnostic_anti_overfit_guard={
                "status": "blocked",
                "plan_only": False,
                "live_provider_invoked": True,
                "fooddb_used": True,
                "summary": {
                    "fixed_case_matrix_used": False,
                    "case_count": 1,
                    "compound_cases": 0,
                    "ambiguity_cases": 0,
                },
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_anti_overfit_guard" in pack["missing_evidence"]
    assert "context_live_diagnostic_anti_overfit_guard_live_provider_invoked" in pack["blockers"]
    assert "context_live_diagnostic_anti_overfit_guard_fooddb_used" in pack["blockers"]
    assert "context_live_diagnostic_anti_overfit_guard_fixed_case_matrix_missing" in pack["blockers"]
    assert "context_live_diagnostic_anti_overfit_guard_case_count_too_low" in pack["blockers"]
    assert "context_live_diagnostic_anti_overfit_guard_compound_case_missing" in pack["blockers"]
    assert "context_live_diagnostic_anti_overfit_guard_ambiguity_case_missing" in pack["blockers"]


def test_pre_live_decision_pack_blocks_unsafe_context_live_holdout_plan() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_diagnostic_holdout_plan={
                "status": "pass",
                "plan_only": False,
                "fixed_case_matrix_used": False,
                "holdout_variants_withheld_from_default_live_prompt": False,
                "ad_hoc_live_case_selection_allowed": True,
                "provider_optimized_case_selection_allowed": True,
                "live_provider_invoked": True,
                "fooddb_used": True,
                "summary": {
                    "case_count": 1,
                    "withheld_holdout_variant_count": 1,
                    "cases_with_holdouts": 1,
                    "compound_cases": 0,
                    "ambiguity_cases": 0,
                },
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_holdout_plan" in pack["missing_evidence"]
    assert "context_live_diagnostic_holdout_plan_live_provider_invoked" in pack["blockers"]
    assert "context_live_diagnostic_holdout_plan_fooddb_used" in pack["blockers"]
    assert "context_live_diagnostic_holdout_plan_fixed_case_matrix_missing" in pack["blockers"]
    assert "context_live_diagnostic_holdout_plan_holdouts_not_withheld" in pack["blockers"]
    assert "context_live_diagnostic_holdout_plan_ad_hoc_case_selection_allowed" in pack["blockers"]
    assert (
        "context_live_diagnostic_holdout_plan_provider_optimized_selection_allowed"
        in pack["blockers"]
    )
    assert "context_live_diagnostic_holdout_plan_withheld_holdout_count_too_low" in pack["blockers"]


def test_pre_live_decision_pack_blocks_unsafe_context_live_case_matrix() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_diagnostic_case_matrix={
                "status": "pass",
                "plan_only": False,
                "live_provider_invoked": True,
                "live_provider_approved": True,
                "fooddb_used": True,
                "summary": {"case_count": 3, "compound_cases": 0},
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_case_matrix" in pack["missing_evidence"]
    assert "context_live_diagnostic_case_matrix_live_provider_invoked" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_live_provider_approved" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_fooddb_used" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_case_count_too_low" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_compound_case_missing" in pack["blockers"]


def test_pre_live_decision_pack_blocks_when_pl_ce_local_review_gate_is_blocked() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            **{
                CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: {
                    "status": "blocked",
                    "ready_for_live_diagnostic_decision": False,
                }
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID in pack["missing_evidence"]
    assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is False
    assert "live_canary_approved" not in pack


def test_pre_live_decision_pack_blocks_pl_ce_local_review_overclaims() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            **{
                CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: {
                    "status": CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
                "ready_for_live_diagnostic_decision": True,
                "ready_for_fdb_integration": True,
                "real_fooddb_pass_claimed": True,
                "private_self_use_approved": True,
                }
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert (
        f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID}_ready_for_live_diagnostic_decision"
        in pack["blockers"]
    )
    assert (
        f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID}_ready_for_fdb_integration"
        in pack["blockers"]
    )
    assert (
        f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID}_real_fooddb_pass_claimed"
        in pack["blockers"]
    )
    assert (
        f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID}_private_self_use_approved"
        in pack["blockers"]
    )
    assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is False
    _assert_removed_fixed_false_outputs(pack)


def test_pre_live_decision_pack_blocks_shared_contract_changes() -> None:
    for flag in (
        "shared_contract_changed",
        "manager_context_packet_schema_changed",
        "nutrition_evidence_store_port_changed",
        "food_evidence_record_schema_changed",
        "packet_ready_anchor_schema_changed",
        "packetizer_format_changed",
        "basket_semantics_changed",
        "food_evidence_promotion_policy_changed",
    ):
        pack = build_pre_live_self_use_decision_pack(
            _evidence(
                **{
                    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID: {
                        "status": CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
                        flag: True,
                    }
                }
            )
        )

        assert pack["selected_option"] == "stay_local_self_use"
        assert f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID}_{flag}" in pack["blockers"]
        assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is False


def test_pre_live_decision_pack_does_not_accept_pl_ce_status_for_other_evidence() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(phase_c_gate={"status": "ready_for_human_pl_ce_review"})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "phase_c_gate" in pack["missing_evidence"]
    assert pack[CURRENT_SHELL_COMPATIBILITY_READY_FOR_LOCAL_REVIEW_FLAG] is True


def test_pre_live_decision_pack_script_writes_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "pre_live_pack.json"
    evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_pre_live_self_use_decision_pack import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert "live_canary_approved" not in artifact


def test_pre_live_axis_summary_source_stays_out_of_fooddb_live_and_shared_contracts() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path("scripts/accurate_intake_pre_live_axis_summary.py"),
            Path("scripts/build_accurate_intake_pre_live_self_use_decision_pack.py"),
        )
    )
    forbidden_fragments = (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "ManagerContextPacket",
        "TavilyClient",
        "selected_extract",
        "fooddb_truth_updated = True",
        "live_llm_invoked = True",
        "ready_for_live_diagnostic_decision = True",
        "private_self_use_approved = True",
    )

    for fragment in forbidden_fragments:
        assert fragment not in combined
