from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (
    REQUIRED_PRE_LIVE_EVIDENCE,
    build_pre_live_self_use_decision_pack,
)


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
        "pl_ce_local_review_decision_pack": {
            "status": "ready_for_human_pl_ce_review",
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "real_fooddb_pass_claimed": False,
            "private_self_use_approved": False,
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
    assert pack["live_llm_invoked"] is False
    assert pack["live_canary_approved"] is False
    assert pack["kimi_active_runtime_default_allowed"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["runtime_web_activation_approved"] is False
    assert pack["blockers"] == []


def test_pre_live_decision_pack_stays_local_when_review_or_data_hygiene_evidence_missing() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            dogfood_review_queue={"status": "missing"},
            local_dogfood_data_hygiene={"status": "blocked"},
            local_operator_data_hygiene_bundle={},
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert pack["live_canary_approved"] is False
    assert pack["missing_evidence"] == [
        "dogfood_review_queue",
        "local_dogfood_data_hygiene",
        "local_operator_data_hygiene_bundle",
    ]


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
    assert pack["live_canary_approved"] is False


def test_pre_live_decision_pack_requires_browser_executed_evidence_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(browser_shell_smoke={"status": "blocked", "browser_executed": False})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "browser_shell_smoke" in pack["missing_evidence"]
    assert pack["evidence_status"]["browser_shell_smoke"]["browser_executed"] is False


def test_pre_live_decision_pack_requires_pl_ce_local_review_gate_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(pl_ce_local_review_decision_pack={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "pl_ce_local_review_decision_pack" in pack["missing_evidence"]
    assert pack["ready_for_pl_ce_local_review"] is False
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_requires_context_live_case_matrix_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_case_matrix={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_case_matrix" in pack["missing_evidence"]
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_requires_manager_intent_readiness_pack() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(manager_intent_readiness_review_pack={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "manager_intent_readiness_review_pack" in pack["missing_evidence"]
    assert pack["ready_for_live_diagnostic_decision"] is False


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
    assert pack["ready_for_live_diagnostic_decision"] is False


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
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_requires_context_live_provider_input_preflight() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_provider_input_preflight={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_provider_input_preflight" in pack["missing_evidence"]
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_requires_context_live_response_contract_dry_run() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_response_contract_dry_run={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_response_contract_dry_run" in pack["missing_evidence"]
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_requires_context_live_diagnostic_gate() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_gate={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_gate" in pack["missing_evidence"]
    assert pack["ready_for_live_diagnostic_decision"] is False


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
            pl_ce_local_review_decision_pack={
                "status": "blocked",
                "ready_for_live_diagnostic_decision": False,
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "pl_ce_local_review_decision_pack" in pack["missing_evidence"]
    assert pack["ready_for_pl_ce_local_review"] is False
    assert pack["live_canary_approved"] is False


def test_pre_live_decision_pack_blocks_pl_ce_local_review_overclaims() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            pl_ce_local_review_decision_pack={
                "status": "ready_for_human_pl_ce_review",
                "ready_for_live_diagnostic_decision": True,
                "ready_for_fdb_integration": True,
                "real_fooddb_pass_claimed": True,
                "private_self_use_approved": True,
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "pl_ce_local_review_decision_pack_ready_for_live_diagnostic_decision" in pack["blockers"]
    assert "pl_ce_local_review_decision_pack_ready_for_fdb_integration" in pack["blockers"]
    assert "pl_ce_local_review_decision_pack_real_fooddb_pass_claimed" in pack["blockers"]
    assert "pl_ce_local_review_decision_pack_private_self_use_approved" in pack["blockers"]
    assert pack["ready_for_pl_ce_local_review"] is False
    assert pack["ready_for_live_diagnostic_decision"] is False


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
            _evidence(pl_ce_local_review_decision_pack={
                "status": "ready_for_human_pl_ce_review",
                flag: True,
            })
        )

        assert pack["selected_option"] == "stay_local_self_use"
        assert f"pl_ce_local_review_decision_pack_{flag}" in pack["blockers"]
        assert pack["ready_for_pl_ce_local_review"] is False


def test_pre_live_decision_pack_does_not_accept_pl_ce_status_for_other_evidence() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(phase_c_gate={"status": "ready_for_human_pl_ce_review"})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "phase_c_gate" in pack["missing_evidence"]
    assert pack["ready_for_pl_ce_local_review"] is True


def test_pre_live_decision_pack_script_writes_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "pre_live_pack.json"
    evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_pre_live_self_use_decision_pack import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert artifact["live_canary_approved"] is False
