from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_conditioned_intent_wall import (
    build_context_conditioned_intent_wall_artifact,
)
from app.composition.accurate_intake_correction_removal_fixture_flow import (
    build_correction_removal_fixture_flow_artifact,
)
from app.composition.accurate_intake_responder_input_contract_fake_smoke import (
    build_responder_input_contract_fake_smoke_artifact,
)


_REQUIRED_INTERACTION_IDS = (
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


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _context_wall_by_id() -> dict[str, dict[str, Any]]:
    artifact = build_context_conditioned_intent_wall_artifact()
    return {
        str(scenario.get("scenario_id") or ""): scenario
        for scenario in artifact.get("scenarios", [])
        if isinstance(scenario, dict)
    }


def _correction_flow_by_id() -> dict[str, dict[str, Any]]:
    artifact = build_correction_removal_fixture_flow_artifact()
    return {
        str(scenario.get("scenario_id") or ""): scenario
        for scenario in artifact.get("scenarios", [])
        if isinstance(scenario, dict)
    }


def _responder_scenarios_by_id() -> dict[str, dict[str, Any]]:
    artifact = build_responder_input_contract_fake_smoke_artifact()
    return {
        str(scenario.get("scenario_id") or ""): scenario
        for scenario in artifact.get("scenarios", [])
        if isinstance(scenario, dict)
    }


def _interaction(
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
    return _json_safe(
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


def _interactions() -> list[dict[str, Any]]:
    return [
        _interaction(
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
        _interaction(
            interaction_id="modify_drink_sugar_no_prior_drink",
            user_utterance_family="change_sugar_without_prior_drink",
            context_wall_scenario_id="half_sugar_no_prior_drink",
            expected_semantic_posture="clarification_required",
            workflow_effect="clarification_only",
            ui_render_obligation="render_not_enough_context",
            responder_allowed_fact_scenario_id="clarification_no_commit",
        ),
        _interaction(
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
        _interaction(
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
        _interaction(
            interaction_id="remove_tofu_no_luwei_context",
            user_utterance_family="remove_named_item_without_context",
            context_wall_scenario_id="remove_tofu_no_luwei_context",
            expected_semantic_posture="clarification_required",
            workflow_effect="clarification_only",
            ui_render_obligation="render_not_enough_context",
            responder_allowed_fact_scenario_id="clarification_no_commit",
        ),
        _interaction(
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
        _interaction(
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
        _interaction(
            interaction_id="previous_drink_calorie_query",
            user_utterance_family="query_previous_drink_calorie",
            context_wall_scenario_id="previous_drink_calorie_query",
            expected_semantic_posture="query_no_mutation",
            workflow_effect="query_only",
            ui_render_obligation="render_read_only_answer_facts",
            responder_allowed_fact_scenario_id="candidate_supported_no_mutation",
            query_no_mutation=True,
        ),
        _interaction(
            interaction_id="daily_target_update_1800",
            user_utterance_family="explicit_daily_target_update",
            context_wall_scenario_id="explicit_daily_target_1800",
            expected_semantic_posture="daily_target_update_candidate",
            workflow_effect="target_update_candidate",
            ui_render_obligation="render_manager_decision_trace_only",
            responder_allowed_fact_scenario_id="committed_backend_budget",
            target_update_requires_manager_decision=True,
        ),
        _interaction(
            interaction_id="meal_estimate_800_not_target",
            user_utterance_family="meal_kcal_estimate_statement",
            context_wall_scenario_id="meal_estimate_800_not_target",
            expected_semantic_posture="meal_estimate_context",
            workflow_effect="meal_estimate_context",
            ui_render_obligation="render_estimate_context_not_daily_target",
            responder_allowed_fact_scenario_id="committed_backend_budget",
        ),
        _interaction(
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


def _validate(
    interactions: list[dict[str, Any]],
    *,
    context_wall: dict[str, dict[str, Any]],
    correction_flow: dict[str, dict[str, Any]],
    responder_scenarios: dict[str, dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    interaction_ids = [str(row.get("interaction_id") or "") for row in interactions]
    if interaction_ids != list(_REQUIRED_INTERACTION_IDS):
        blockers.append("required_interaction_order_mismatch")
    for row in interactions:
        row_id = str(row.get("interaction_id") or "unknown")
        context_wall_id = str(row.get("context_wall_scenario_id") or "")
        context_row = context_wall.get(context_wall_id)
        if context_row is None:
            blockers.append(f"{row_id}.context_wall_scenario_missing")
        else:
            if context_row.get("expected_semantic_posture") != row.get("expected_semantic_posture"):
                blockers.append(f"{row_id}.context_wall_posture_mismatch")
            if row.get("pending_followup_required") is True:
                if context_row.get("pending_followup_carryover") is not True:
                    blockers.append(f"{row_id}.pending_followup_not_carried")
            if row.get("pending_draft_required") is True:
                if context_row.get("pending_draft_present") is not True:
                    blockers.append(f"{row_id}.pending_draft_not_present")
            if row.get("target_candidates_required") is True:
                if int(context_row.get("target_candidate_count") or 0) < 1:
                    blockers.append(f"{row_id}.context_wall_target_candidates_missing")
            if row.get("ambiguity_must_be_preserved") is True:
                if context_row.get("ambiguity_preserved") is not True:
                    blockers.append(f"{row_id}.context_wall_ambiguity_not_preserved")
            if row.get("query_no_mutation") is True:
                if context_row.get("query_no_mutation") is not True:
                    blockers.append(f"{row_id}.context_wall_query_no_mutation_missing")
            if row.get("target_update_requires_manager_decision") is True:
                if context_row.get("target_update_requires_manager_decision") is not True:
                    blockers.append(f"{row_id}.context_wall_target_update_manager_decision_missing")

        correction_flow_id = row.get("correction_flow_scenario_id")
        if correction_flow_id is not None:
            flow_row = correction_flow.get(str(correction_flow_id))
            if flow_row is None:
                blockers.append(f"{row_id}.correction_flow_scenario_missing")
            elif row.get("ambiguity_must_be_preserved") is True:
                if flow_row.get("ambiguity_preserved") is not True:
                    blockers.append(f"{row_id}.correction_flow_ambiguity_not_preserved")
            elif row.get("target_candidates_required") is True:
                if int(flow_row.get("target_candidate_count") or 0) < 1:
                    blockers.append(f"{row_id}.correction_flow_target_candidates_missing")

        responder_id = row.get("responder_allowed_fact_scenario_id")
        if responder_id is None:
            blockers.append(f"{row_id}.responder_scenario_missing")
        elif str(responder_id) not in responder_scenarios:
            blockers.append(f"{row_id}.responder_scenario_missing")
        else:
            responder_row = responder_scenarios[str(responder_id)]
            if responder_row.get("accepted_response", {}).get("verdict") != "accepted":
                blockers.append(f"{row_id}.responder_accepted_response_not_accepted")

        if row.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append(f"{row_id}.semantic_owner_not_fixture_manager")
        if row.get("manager_fixture_semantic_source_used") is not True:
            blockers.append(f"{row_id}.manager_fixture_semantic_source_missing")
        if row.get("deterministic_supplies_candidates_and_pins_only") is not True:
            blockers.append(f"{row_id}.deterministic_not_limited_to_context_support")
        if row.get("deterministic_selected_intent") is not False:
            blockers.append(f"{row_id}.deterministic_selected_intent")
        if row.get("deterministic_selected_target") is not False:
            blockers.append(f"{row_id}.deterministic_selected_target")
        if row.get("deterministic_semantic_inference_used") is not False:
            blockers.append(f"{row_id}.deterministic_semantic_inference_used")
        if row.get("frontend_render_only") is not True:
            blockers.append(f"{row_id}.frontend_not_render_only")
        if row.get("frontend_semantic_owner") is not False:
            blockers.append(f"{row_id}.frontend_semantic_owner")
        if row.get("frontend_raw_text_semantic_router") is not False:
            blockers.append(f"{row_id}.frontend_raw_text_semantic_router")
        if row.get("frontend_selects_target") is not False:
            blockers.append(f"{row_id}.frontend_selects_target")
        if row.get("mutation_authority") is not False:
            blockers.append(f"{row_id}.mutation_authority")
        if row.get("manager_context_packet_schema_changed") is not False:
            blockers.append(f"{row_id}.manager_context_packet_schema_changed")
    return blockers


def build_contextual_interaction_matrix_artifact() -> dict[str, Any]:
    context_wall = _context_wall_by_id()
    correction_flow = _correction_flow_by_id()
    responder_scenarios = _responder_scenarios_by_id()
    interactions = _interactions()
    blockers = _validate(
        interactions,
        context_wall=context_wall,
        correction_flow=correction_flow,
        responder_scenarios=responder_scenarios,
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_contextual_interaction_matrix",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_pl_ce_short_term_context_interaction_matrix",
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "semantic_owner": "fixture_manager_structured_decision",
            "manager_fixture_semantic_source_used": True,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "frontend_render_only": True,
            "frontend_semantic_owner": False,
            "frontend_raw_text_semantic_router": False,
            "frontend_selects_target": False,
            "mutation_authority": False,
            "mutation_changed": False,
            "runtime_truth_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "fooddb_truth_changed": False,
            "fooddb_truth_updated": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "production_db_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "interaction_count": len(interactions),
                "pending_followup_interactions": sum(
                    1 for row in interactions if row["pending_followup_required"]
                ),
                "target_candidate_interactions": sum(
                    1 for row in interactions if row["target_candidates_required"]
                ),
                "ambiguity_preserved_interactions": sum(
                    1 for row in interactions if row["ambiguity_must_be_preserved"]
                ),
                "query_no_mutation_interactions": sum(
                    1 for row in interactions if row["query_no_mutation"]
                ),
                "target_update_manager_decision_interactions": sum(
                    1 for row in interactions if row["target_update_requires_manager_decision"]
                ),
            },
            "interactions": interactions,
        }
    )


__all__ = ["build_contextual_interaction_matrix_artifact"]
