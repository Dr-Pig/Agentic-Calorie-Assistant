from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "quality" / "advanced_capability_activation_ladder.yaml"
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _contract() -> dict[str, object]:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _section(content: str, heading: str, next_heading: str) -> str:
    start = content.index(heading)
    end = content.index(next_heading, start)
    return content[start:end]


def test_activation_ladder_is_indexed_without_bootstrap_takeover() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")
    active_bootstrap = _section(doc_index, "## Active Bootstrap", "## Active Truth Rules")

    assert "advanced_capability_activation_ladder.yaml" in doc_index
    assert "advanced capability activation ladder" in doc_index
    assert "advanced_capability_activation_ladder.yaml" not in active_bootstrap


def test_activation_ladder_preserves_stage_order_and_one_step_promotion() -> None:
    contract = _contract()

    assert contract["stage_order"] == [
        "contract",
        "fake",
        "deterministic",
        "live_diagnostic",
        "shadow",
        "read_only_runtime",
        "canary",
        "user_facing",
        "mutation_bearing",
    ]
    assert contract["promotion_rules"]["one_step_promotion_only"] is True
    assert contract["promotion_rules"]["human_review_required_for_stage_change"] is True
    assert contract["promotion_rules"]["evidence_must_name_holdouts"] is True
    assert contract["promotion_rules"]["rollback_or_kill_switch_required_from"] == [
        "canary",
        "user_facing",
        "mutation_bearing",
    ]


def test_all_advanced_capabilities_have_explicit_current_stage_and_dependencies() -> None:
    contract = _contract()
    capabilities = contract["capabilities"]

    assert set(capabilities) == {
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
    }
    assert capabilities["long_term_memory"]["current_stage"] == "read_only_runtime"
    assert capabilities["long_term_memory"]["next_allowed_stage"] == "canary"
    assert capabilities["recommendation"]["current_stage"] == "read_only_runtime"
    assert capabilities["recommendation"]["next_allowed_stage"] == "canary"
    assert capabilities["rescue"]["current_stage"] == "read_only_runtime"
    assert capabilities["rescue"]["next_allowed_stage"] == "canary"
    assert capabilities["proactive"]["current_stage"] == "read_only_runtime"
    assert capabilities["proactive"]["next_allowed_stage"] == "canary"
    assert capabilities["recommendation"]["depends_on"] == [
        "long_term_memory.read_only_runtime"
    ]
    assert capabilities["rescue"]["depends_on"] == [
        "long_term_memory.read_only_runtime"
    ]
    assert capabilities["proactive"]["depends_on"] == [
        "long_term_memory.read_only_runtime",
        "recommendation.read_only_runtime",
        "rescue.read_only_runtime",
    ]


def test_ltm_read_only_runtime_stage_is_backed_by_manual_transition_artifact() -> None:
    contract = _contract()
    ltm = contract["capabilities"]["long_term_memory"]
    evidence = ltm["stage_transition_evidence"]

    assert evidence == {
        "artifact_type": "runtime_lab_memory_stage_promotion_decision",
        "status": "approved",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "current_stage_in_decision_artifact": "shadow",
        "target_stage_in_decision_artifact": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "required_source_pack": "runtime_lab_memory_read_only_runtime_lab_pack",
        "required_human_review_artifact": (
            "runtime_lab_memory_stage_promotion_review_decision"
        ),
    }
    assert "runtime_lab_memory_stage_promotion_decision" in ltm[
        "current_allowed_outputs"
    ]
    assert "shadow_memory_context_pack" in ltm["current_allowed_outputs"]
    assert "runtime_lab_memory_consumer_summary_projection" in ltm[
        "current_allowed_outputs"
    ]
    assert ltm["stage_specific_no_go"] == {
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "cross_session_personalization_allowed": False,
    }


def test_recommendation_read_only_runtime_stage_is_backed_by_manual_transition_artifact() -> None:
    contract = _contract()
    recommendation = contract["capabilities"]["recommendation"]
    evidence = recommendation["stage_transition_evidence"]

    assert evidence == {
        "artifact_type": "recommendation_read_only_runtime_stage_decision",
        "status": "approved",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "current_stage_in_decision_artifact": "shadow",
        "target_stage_in_decision_artifact": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "dependency_satisfied": "long_term_memory.read_only_runtime",
        "required_preflight_artifact": "recommendation_read_only_runtime_preflight",
        "required_human_review_artifact": (
            "recommendation_read_only_runtime_stage_review_decision"
        ),
    }
    assert "recommendation_read_only_runtime_stage_decision" in recommendation[
        "current_allowed_outputs"
    ]
    assert "recommendation_read_only_runtime_preflight" in recommendation[
        "current_allowed_outputs"
    ]
    assert "recommendation_three_node_shadow_artifact" in recommendation[
        "current_allowed_outputs"
    ]
    assert recommendation["stage_specific_no_go"] == {
        "recommendation_served": False,
        "live_search_allowed": False,
        "app_open_recommendation_serving": False,
    }


def test_rescue_read_only_runtime_stage_is_backed_by_manual_transition_artifact() -> None:
    contract = _contract()
    rescue = contract["capabilities"]["rescue"]
    evidence = rescue["stage_transition_evidence"]

    assert evidence == {
        "artifact_type": "rescue_read_only_runtime_stage_decision",
        "status": "approved",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "current_stage_in_decision_artifact": "shadow",
        "target_stage_in_decision_artifact": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "dependency_satisfied": "long_term_memory.read_only_runtime",
        "required_preflight_artifact": "rescue_read_only_runtime_preflight_report",
        "required_human_review_artifact": (
            "rescue_read_only_runtime_stage_review_decision"
        ),
    }
    assert "rescue_read_only_runtime_stage_decision" in rescue[
        "current_allowed_outputs"
    ]
    assert "rescue_read_only_runtime_preflight_report" in rescue[
        "current_allowed_outputs"
    ]
    assert "rescue_no_commit_viability_shadow_packet" in rescue[
        "current_allowed_outputs"
    ]
    assert rescue["stage_specific_no_go"] == {
        "rescue_proposal_committed": False,
        "budget_mutation_allowed": False,
        "proposal_acceptance_route_allowed": False,
    }


def test_proactive_read_only_runtime_stage_is_backed_by_manual_transition_artifact() -> None:
    contract = _contract()
    proactive = contract["capabilities"]["proactive"]
    evidence = proactive["stage_transition_evidence"]

    assert evidence == {
        "artifact_type": "proactive_read_only_runtime_stage_decision",
        "status": "approved",
        "stage_change_recorded": True,
        "manual_promotion_approved": True,
        "current_stage_in_decision_artifact": "shadow",
        "target_stage_in_decision_artifact": "read_only_runtime",
        "activation_stage_after_decision": "read_only_runtime",
        "dependencies_satisfied": [
            "recommendation.read_only_runtime",
            "rescue.read_only_runtime",
        ],
        "required_preflight_artifact": "proactive_read_only_runtime_preflight_report",
        "required_human_review_artifact": (
            "proactive_read_only_runtime_stage_review_decision"
        ),
    }
    assert "proactive_read_only_runtime_stage_decision" in proactive[
        "current_allowed_outputs"
    ]
    assert "proactive_read_only_runtime_preflight_report" in proactive[
        "current_allowed_outputs"
    ]
    assert "proactive_no_send_decision_pack" in proactive["current_allowed_outputs"]
    assert proactive["stage_specific_no_go"] == {
        "scheduler_activation_allowed": False,
        "notification_delivery_allowed": False,
        "trigger_persistence_allowed": False,
    }


def test_pre_promotion_no_go_flags_block_runtime_drift() -> None:
    contract = _contract()
    no_go = contract["pre_promotion_no_go_flags"]

    assert no_go["applies_to"] == "mainline_runtime_activation"
    for field in (
        "user_facing_behavior_changed",
        "canonical_mutation_changed",
        "durable_product_memory_written",
        "manager_context_packet_changed",
        "scheduler_activation_allowed",
        "notification_delivery_allowed",
        "recommendation_served",
        "rescue_proposal_committed",
        "route_or_api_activation_allowed",
        "product_db_migration_allowed",
        "live_provider_delivery_path_allowed",
    ):
        assert no_go[field] is False


def test_read_only_runtime_stage_allows_observation_without_authority() -> None:
    contract = _contract()
    read_only_runtime = contract["stage_requirements"]["read_only_runtime"]

    assert read_only_runtime["runtime_connected"] is True
    assert read_only_runtime["user_facing_behavior_changed"] is False
    assert read_only_runtime["canonical_mutation_changed"] is False
    assert read_only_runtime["manager_context_packet_changed"] is False
    assert read_only_runtime["durable_product_memory_written"] is False
    assert read_only_runtime["allowed_outputs"] == [
        "read_only_runtime_trace",
        "shadow_context_pack",
        "paired_baseline_comparison",
        "omission_trace",
    ]


def test_shadow_lab_can_build_complete_product_capability_without_mainline_activation() -> None:
    contract = _contract()
    lab_scope = contract["shadow_lab_scope"]

    assert lab_scope["goal"] == "complete_product_capability_and_ux_tasks"
    assert lab_scope["complete_product_capability_allowed"] is True
    assert lab_scope["lab_only_user_facing_surfaces_allowed"] is True
    assert lab_scope["lab_only_scheduler_simulation_allowed"] is True
    assert lab_scope["lab_only_isolated_mutation_ledger_allowed"] is True
    assert lab_scope["lab_only_durable_memory_store_allowed"] is True
    assert lab_scope["live_llm_diagnostic_allowed"] is True
    assert lab_scope["real_user_feedback_replay_allowed"] is True

    assert lab_scope["mainline_runtime_connection_allowed"] is False
    assert lab_scope["mainline_route_or_api_mount_allowed"] is False
    assert lab_scope["mainline_scheduler_delivery_allowed"] is False
    assert lab_scope["canonical_product_db_mutation_allowed"] is False
    assert lab_scope["manager_context_packet_production_change_allowed"] is False


def test_advanced_lab_execution_policy_locks_provider_surface_and_fooddb_decisions() -> None:
    contract = _contract()
    policy = contract["advanced_lab_execution_policy"]

    assert policy["current_first_slice"] == "advanced_runtime_lab_dormancy_contract"
    assert policy["current_first_slice_live_provider_calls_allowed"] is False
    assert policy["later_lab_live_diagnostics_allowed_after_dormancy_gate"] is True
    assert policy["provider_dependency_inversion_required"] is True
    assert policy["provider_family"] == "builderspace"
    assert policy["diagnostic_live_model"] == "grok-4-fast"
    assert policy["target_reasoning_model"] == "kimi-k2.5"
    assert policy["kimi_live_calls_allowed_in_this_train"] is False
    assert policy["model_profile_seam"] == {
        "default_live_diagnostic_profile_id": (
            "builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic"
        ),
        "target_reasoning_profile_id": (
            "builderspace-kimi-k2-5-advanced-shadow-lab-dormant-reference"
        ),
        "live_provider_calls_allowed_by_default": False,
        "kimi_selection_status": "dormant_reference_only",
        "production_selected": False,
        "provider_specific_product_semantics_allowed": False,
    }
    assert policy["proactive_surface"] == "chat_only"
    assert policy["inbox_mirror_allowed"] is False
    assert policy["push_line_or_os_notification_allowed"] is False
    assert policy["fooddb_expansion_allowed"] is False
    assert policy["fooddb_expansion_requires_real_self_use"] is True
    assert policy["simulated_dogfood_allowed_until_real_traces_exist"] is True
    assert policy["mainline_activation_requires_separate_pr"] is True
    assert all(value is False for value in policy["required_dormant_merge_flags"].values())


def test_lab_complete_capability_requires_explicit_isolation_markers() -> None:
    contract = _contract()
    isolation = contract["shadow_lab_scope"]["required_isolation_markers"]

    assert isolation == {
        "lab_isolated": True,
        "mainline_runtime_connected": False,
        "user_facing_behavior_changed_in_mainline": False,
        "canonical_mutation_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
        "manager_context_packet_changed_in_mainline": False,
        "real_scheduler_or_notification_delivery": False,
        "lab_artifacts_may_include_complete_ux": True,
    }


def test_memory_ux_acceptance_points_to_review_forget_confirmation_controls() -> None:
    contract = _contract()
    entries = {
        entry["journey_id"]: entry
        for entry in contract["edge_case_coverage_contract"]["ux_acceptance_entries"]
    }
    memory_entry = entries["M"]

    assert "memory_lab_review_loop_state" in memory_entry["existing_shadow_artifacts"]
    assert (
        "chat_first_memory_review_correction_surface"
        in memory_entry["existing_shadow_artifacts"]
    )
    assert "review_control_semantics" in memory_entry["required_trace_fields"]
    assert "user_equivalent_memory_control" in memory_entry["required_trace_fields"]
    assert memory_entry["claim_boundary"] == "non_claim"
    assert memory_entry["mainline_activation_allowed"] is False


def test_recommendation_ux_acceptance_points_to_offer_shadow_packet() -> None:
    contract = _contract()
    entries = {
        entry["journey_id"]: entry
        for entry in contract["edge_case_coverage_contract"]["ux_acceptance_entries"]
    }
    recommendation_entry = entries["L"]

    assert (
        "recommendation_offer_shadow_packet"
        in recommendation_entry["existing_shadow_artifacts"]
    )
    assert (
        "recommendation_pending_meal_intent_shadow_packet"
        in recommendation_entry["existing_shadow_artifacts"]
    )
    assert "offer_synthesis_trace" in recommendation_entry["required_trace_fields"]
    assert "acceptance_trace" in recommendation_entry["required_trace_fields"]
    assert "pending_meal_intent_created" in recommendation_entry["required_trace_fields"]
    assert recommendation_entry["acceptance_status"] == "existing_shadow_chain_mapped"
    assert recommendation_entry["claim_boundary"] == "non_claim"
    assert recommendation_entry["mainline_activation_allowed"] is False


def test_planned_event_rescue_acceptance_points_to_negotiation_shadow_packet() -> None:
    contract = _contract()
    entries = {
        entry["journey_id"]: entry
        for entry in contract["edge_case_coverage_contract"]["ux_acceptance_entries"]
    }
    rescue_entry = entries["F2"]

    assert (
        "rescue_planned_event_negotiation_shadow_packet"
        in rescue_entry["existing_shadow_artifacts"]
    )
    assert "planned_event_context" in rescue_entry["required_trace_fields"]
    assert "proposal_candidate" in rescue_entry["required_trace_fields"]
    assert "explicit_accept_required" in rescue_entry["required_trace_fields"]
    assert "budget_mutation_allowed" in rescue_entry["required_trace_fields"]
    assert rescue_entry["acceptance_status"] == "existing_shadow_chain_mapped"
    assert rescue_entry["claim_boundary"] == "non_claim"
    assert rescue_entry["mainline_activation_allowed"] is False


def test_same_day_rescue_acceptance_points_to_chat_negotiation_lifecycle() -> None:
    contract = _contract()
    entries = {
        entry["journey_id"]: entry
        for entry in contract["edge_case_coverage_contract"]["ux_acceptance_entries"]
    }
    rescue_entry = entries["F"]

    assert (
        "rescue_chat_negotiation_lifecycle_shadow_packet"
        in rescue_entry["existing_shadow_artifacts"]
    )
    assert "lifecycle_state" in rescue_entry["required_trace_fields"]
    assert "negotiation_intent" in rescue_entry["required_trace_fields"]
    assert "explicit_accept_required" in rescue_entry["required_trace_fields"]
    assert "dismiss_requested" in rescue_entry["required_trace_fields"]
    assert "proposal_committed" in rescue_entry["required_trace_fields"]
    assert rescue_entry["next_build_slice"] == "advanced_capability_gap_review"
    assert rescue_entry["claim_boundary"] == "non_claim"
    assert rescue_entry["mainline_activation_allowed"] is False


def test_calibration_acceptance_points_to_existing_diagnostic_shadow_chain() -> None:
    contract = _contract()
    entries = {
        entry["journey_id"]: entry
        for entry in contract["edge_case_coverage_contract"]["ux_acceptance_entries"]
    }
    calibration_entry = entries["I"]

    assert "body_calibration_diagnostic_result" in calibration_entry[
        "existing_shadow_artifacts"
    ]
    assert "calibration_proposal_policy_packet" in calibration_entry[
        "existing_shadow_artifacts"
    ]
    assert "calibration_proposal_response_result" in calibration_entry[
        "existing_shadow_artifacts"
    ]
    assert "proposal_policy_packet" in calibration_entry["required_trace_fields"]
    assert "proposal_result" in calibration_entry["required_trace_fields"]
    assert "trace_envelope" in calibration_entry["required_trace_fields"]
    assert "requires_accept_before_plan_mutation" in calibration_entry[
        "required_trace_fields"
    ]
    assert "plan_mutation_authorized" in calibration_entry["required_trace_fields"]
    assert "ledger_mutation_authorized" in calibration_entry["required_trace_fields"]
    assert calibration_entry["acceptance_status"] == "existing_shadow_chain_mapped"
    assert calibration_entry["claim_boundary"] == "non_claim"
    assert calibration_entry["mainline_activation_allowed"] is False


def test_activation_ladder_has_no_remaining_calibration_gap_pointer() -> None:
    contract = _contract()
    entries = contract["edge_case_coverage_contract"]["ux_acceptance_entries"]

    assert all(entry["acceptance_status"] != "gap_requires_next_slice" for entry in entries)
    assert all(
        entry.get("next_build_slice") != "calibration_proposal_shadow_integration"
        for entry in entries
    )


def test_proactive_acceptance_points_to_pending_meal_followup_shadow() -> None:
    contract = _contract()
    entries = {
        entry["journey_id"]: entry
        for entry in contract["edge_case_coverage_contract"]["ux_acceptance_entries"]
    }
    proactive_entry = entries["N"]

    assert (
        "proactive_pending_meal_followup_shadow"
        in proactive_entry["existing_shadow_artifacts"]
    )
    assert "pending_meal_intent_trace" in proactive_entry["required_trace_fields"]
    assert "followup_source_review" in proactive_entry["required_trace_fields"]
    assert "no_send_candidate" in proactive_entry["required_trace_fields"]
    assert "simulation_input" in proactive_entry["required_trace_fields"]
    assert "pending_intent_mutated" in proactive_entry["required_trace_fields"]
    assert proactive_entry["next_build_slice"] == "advanced_capability_gap_review"
    assert proactive_entry["claim_boundary"] == "non_claim"
    assert proactive_entry["mainline_activation_allowed"] is False


def test_contract_records_best_practice_and_harness_minimization_boundaries() -> None:
    contract = _contract()
    best_practice = contract["best_practice_evidence"]
    harness = contract["harness_minimization"]

    assert best_practice["required"] is True
    assert {
        "openai_agents_guardrails",
        "openai_agent_evals",
        "openai_agents_sessions",
        "openai_agents_sandbox_memory",
    }.issubset(set(best_practice["sources_checked"]))
    assert "separate_session_history_from_durable_memory" in best_practice["adopted_guidance"]
    assert "trace_grading_before_repeatable_eval_runs" in best_practice["adopted_guidance"]
    assert "tool_guardrails_for_side_effectful_tool_calls" in best_practice["adopted_guidance"]

    assert harness == {
        "artifact_classification": "manual_promotion",
        "required_merge_check": False,
        "owner": "MemoryRuntimeArchitecture",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_product_runtime_activation_ledger_entries",
        "new_report_family_created": False,
    }
