from __future__ import annotations

import json
from typing import Any


REQUIRED_INTERACTION_IDS = (
    "pending_luwei_components_answer",
    "modify_drink_sugar_no_prior_drink",
    "modify_drink_sugar_one_prior_drink",
    "modify_drink_sugar_multiple_drinks",
    "remove_tofu_no_luwei_context",
    "remove_tofu_one_luwei",
    "remove_tofu_multiple_targets",
    "previous_drink_calorie_query",
    "daily_target_update_1800",
    "meal_estimate_800_not_target",
    "long_session_less_rice",
)


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def interaction(
    *,
    interaction_id: str,
    user_utterance_family: str,
    context_wall_scenario_id: str,
    expected_semantic_posture: str,
    workflow_effect: str,
    ui_render_obligation: str,
    correction_flow_scenario_id: str | None = None,
    responder_allowed_fact_scenario_id: str | None = None,
    pending_followup_required: bool = False,
    pending_draft_required: bool = False,
    target_candidates_required: bool = False,
    ambiguity_must_be_preserved: bool = False,
    query_no_mutation: bool = False,
    target_update_requires_manager_decision: bool = False,
) -> dict[str, Any]:
    return json_safe(
        {
            "interaction_id": interaction_id,
            "user_utterance_family": user_utterance_family,
            "context_wall_scenario_id": context_wall_scenario_id,
            "correction_flow_scenario_id": correction_flow_scenario_id,
            "responder_allowed_fact_scenario_id": responder_allowed_fact_scenario_id,
            "expected_semantic_posture": expected_semantic_posture,
            "workflow_effect": workflow_effect,
            "ui_render_obligation": ui_render_obligation,
            "required_structured_sources": [
                "manager_context_packet_v1_summary",
                "backend_context_loading_artifact",
                "fixture_manager_structured_decision",
            ],
            "pending_followup_required": pending_followup_required,
            "pending_draft_required": pending_draft_required,
            "target_candidates_required": target_candidates_required,
            "ambiguity_must_be_preserved": ambiguity_must_be_preserved,
            "query_no_mutation": query_no_mutation,
            "target_update_requires_manager_decision": target_update_requires_manager_decision,
            "semantic_owner": "fixture_manager_structured_decision",
            "manager_fixture_semantic_source_used": True,
            "deterministic_role": "supply_context_candidates_pins_and_validate_boundaries",
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "frontend_render_source": "backend_structured_context_and_read_models",
            "frontend_render_only": True,
            "frontend_semantic_owner": False,
            "frontend_raw_text_semantic_router": False,
            "frontend_selects_target": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
        }
    )


def interactions() -> list[dict[str, Any]]:
    return [
        interaction(
            interaction_id="pending_luwei_components_answer",
            user_utterance_family="listed_components_after_luwei_followup",
            context_wall_scenario_id="luwei_pending_components_followup",
            expected_semantic_posture="attach_to_pending_draft",
            workflow_effect="complete_pending_draft_candidate",
            ui_render_obligation="render_pending_followup_context",
            responder_allowed_fact_scenario_id="clarification_no_commit",
            pending_followup_required=True,
            pending_draft_required=True,
        ),
        interaction(
            interaction_id="modify_drink_sugar_no_prior_drink",
            user_utterance_family="change_sugar_without_prior_drink",
            context_wall_scenario_id="half_sugar_no_prior_drink",
            expected_semantic_posture="clarification_required",
            workflow_effect="clarification_only",
            ui_render_obligation="render_not_enough_context",
            responder_allowed_fact_scenario_id="clarification_no_commit",
        ),
        interaction(
            interaction_id="modify_drink_sugar_one_prior_drink",
            user_utterance_family="change_sugar_with_one_prior_drink",
            context_wall_scenario_id="half_sugar_one_prior_drink",
            correction_flow_scenario_id="modify_drink_sugar_candidate",
            expected_semantic_posture="correction_candidate_available",
            workflow_effect="correction_candidate",
            ui_render_obligation="render_read_only_target_candidates",
            responder_allowed_fact_scenario_id="candidate_supported_no_mutation",
            target_candidates_required=True,
        ),
        interaction(
            interaction_id="modify_drink_sugar_multiple_drinks",
            user_utterance_family="change_sugar_with_multiple_prior_drinks",
            context_wall_scenario_id="half_sugar_multiple_drinks",
            correction_flow_scenario_id="correct_previous_identity_ambiguous",
            expected_semantic_posture="ambiguous_target",
            workflow_effect="ambiguity_clarification",
            ui_render_obligation="render_ambiguity_without_target_selection",
            responder_allowed_fact_scenario_id="correction_ambiguity",
            target_candidates_required=True,
            ambiguity_must_be_preserved=True,
        ),
        interaction(
            interaction_id="remove_tofu_no_luwei_context",
            user_utterance_family="remove_named_item_without_context",
            context_wall_scenario_id="remove_tofu_no_luwei_context",
            expected_semantic_posture="clarification_required",
            workflow_effect="clarification_only",
            ui_render_obligation="render_not_enough_context",
            responder_allowed_fact_scenario_id="clarification_no_commit",
        ),
        interaction(
            interaction_id="remove_tofu_one_luwei",
            user_utterance_family="remove_named_item_with_one_luwei",
            context_wall_scenario_id="remove_tofu_one_luwei",
            correction_flow_scenario_id="remove_named_item_candidate",
            expected_semantic_posture="removal_candidate_available",
            workflow_effect="removal_candidate",
            ui_render_obligation="render_read_only_target_candidates",
            responder_allowed_fact_scenario_id="candidate_supported_no_mutation",
            target_candidates_required=True,
        ),
        interaction(
            interaction_id="remove_tofu_multiple_targets",
            user_utterance_family="remove_named_item_with_multiple_targets",
            context_wall_scenario_id="remove_tofu_multiple_targets",
            correction_flow_scenario_id="remove_previous_item_ambiguous",
            expected_semantic_posture="ambiguous_target",
            workflow_effect="ambiguity_clarification",
            ui_render_obligation="render_ambiguity_without_target_selection",
            responder_allowed_fact_scenario_id="correction_ambiguity",
            target_candidates_required=True,
            ambiguity_must_be_preserved=True,
        ),
        interaction(
            interaction_id="previous_drink_calorie_query",
            user_utterance_family="query_previous_drink_calorie",
            context_wall_scenario_id="previous_drink_calorie_query",
            expected_semantic_posture="query_no_mutation",
            workflow_effect="query_only",
            ui_render_obligation="render_read_only_answer_facts",
            responder_allowed_fact_scenario_id="candidate_supported_no_mutation",
            query_no_mutation=True,
        ),
        interaction(
            interaction_id="daily_target_update_1800",
            user_utterance_family="explicit_daily_target_update",
            context_wall_scenario_id="explicit_daily_target_1800",
            expected_semantic_posture="daily_target_update_candidate",
            workflow_effect="target_update_candidate",
            ui_render_obligation="render_manager_decision_trace_only",
            responder_allowed_fact_scenario_id="committed_backend_budget",
            target_update_requires_manager_decision=True,
        ),
        interaction(
            interaction_id="meal_estimate_800_not_target",
            user_utterance_family="meal_kcal_estimate_statement",
            context_wall_scenario_id="meal_estimate_800_not_target",
            expected_semantic_posture="meal_estimate_context",
            workflow_effect="meal_estimate_context",
            ui_render_obligation="render_estimate_context_not_daily_target",
            responder_allowed_fact_scenario_id="committed_backend_budget",
        ),
        interaction(
            interaction_id="long_session_less_rice",
            user_utterance_family="long_session_change_rice_portion",
            context_wall_scenario_id="long_session_less_rice",
            correction_flow_scenario_id="modify_rice_portion_candidate",
            expected_semantic_posture="correction_candidate_available",
            workflow_effect="correction_candidate",
            ui_render_obligation="render_read_only_target_candidates",
            responder_allowed_fact_scenario_id="candidate_supported_no_mutation",
            target_candidates_required=True,
        ),
    ]


__all__ = ["REQUIRED_INTERACTION_IDS", "interaction", "interactions", "json_safe"]
