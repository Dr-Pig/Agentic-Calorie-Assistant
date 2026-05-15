from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_contextual_interaction_cases import (
    REQUIRED_INTERACTION_IDS,
)


def validate_interactions(
    interactions: list[dict[str, Any]],
    *,
    context_wall: dict[str, dict[str, Any]],
    correction_flow: dict[str, dict[str, Any]],
    responder_scenarios: dict[str, dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    interaction_ids = [str(row.get("interaction_id") or "") for row in interactions]
    if interaction_ids != list(REQUIRED_INTERACTION_IDS):
        blockers.append("required_interaction_order_mismatch")
    for row in interactions:
        row_id = str(row.get("interaction_id") or "unknown")
        _append_context_wall_blockers(blockers, row_id, row, context_wall)
        _append_correction_flow_blockers(blockers, row_id, row, correction_flow)
        _append_responder_blockers(blockers, row_id, row, responder_scenarios)
        _append_ownership_blockers(blockers, row_id, row)
    return blockers


def _append_context_wall_blockers(
    blockers: list[str],
    row_id: str,
    row: dict[str, Any],
    context_wall: dict[str, dict[str, Any]],
) -> None:
    context_wall_id = str(row.get("context_wall_scenario_id") or "")
    context_row = context_wall.get(context_wall_id)
    if context_row is None:
        blockers.append(f"{row_id}.context_wall_scenario_missing")
        return
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


def _append_correction_flow_blockers(
    blockers: list[str],
    row_id: str,
    row: dict[str, Any],
    correction_flow: dict[str, dict[str, Any]],
) -> None:
    correction_flow_id = row.get("correction_flow_scenario_id")
    if correction_flow_id is None:
        return
    flow_row = correction_flow.get(str(correction_flow_id))
    if flow_row is None:
        blockers.append(f"{row_id}.correction_flow_scenario_missing")
    elif row.get("ambiguity_must_be_preserved") is True:
        if flow_row.get("ambiguity_preserved") is not True:
            blockers.append(f"{row_id}.correction_flow_ambiguity_not_preserved")
    elif row.get("target_candidates_required") is True:
        if int(flow_row.get("target_candidate_count") or 0) < 1:
            blockers.append(f"{row_id}.correction_flow_target_candidates_missing")


def _append_responder_blockers(
    blockers: list[str],
    row_id: str,
    row: dict[str, Any],
    responder_scenarios: dict[str, dict[str, Any]],
) -> None:
    responder_id = row.get("responder_allowed_fact_scenario_id")
    if responder_id is None:
        blockers.append(f"{row_id}.responder_scenario_missing")
        return
    responder_row = responder_scenarios.get(str(responder_id))
    if responder_row is None:
        blockers.append(f"{row_id}.responder_scenario_missing")
    elif responder_row.get("accepted_response", {}).get("verdict") != "accepted":
        blockers.append(f"{row_id}.responder_accepted_response_not_accepted")


def _append_ownership_blockers(
    blockers: list[str],
    row_id: str,
    row: dict[str, Any],
) -> None:
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


__all__ = ["validate_interactions"]
