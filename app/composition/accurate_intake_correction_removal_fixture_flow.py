from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_conditioned_intent_wall import (
    build_context_conditioned_intent_wall_artifact,
)


_REQUIRED_SCENARIO_IDS = (
    "remove_previous_item_ambiguous",
    "remove_named_item_candidate",
    "modify_drink_sugar_candidate",
    "modify_rice_portion_candidate",
    "correct_previous_identity_ambiguous",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _candidate(
    target_id: str,
    display_name: str,
    *,
    target_type: str = "meal_item",
    action_affordance: str = "candidate",
) -> dict[str, Any]:
    return {
        "target_object_type": target_type,
        "target_object_id": target_id,
        "display_name": display_name,
        "uniqueness_status": "candidate",
        "action_affordance": action_affordance,
        "read_only": True,
        "mutation_authority": False,
        "render_only": True,
        "frontend_selectable_as_final_target": False,
    }


def _fixture_decision(
    *,
    target_resolution_status: str,
    requires_manager_or_clarification: bool,
) -> dict[str, Any]:
    return {
        "semantic_source": "fixture_manager_structured_decision",
        "target_resolution_status": target_resolution_status,
        "requires_manager_or_clarification": requires_manager_or_clarification,
        "deterministic_role": "supply_context_candidates_and_validate_boundaries",
    }


def _scenario(
    *,
    scenario_id: str,
    raw_user_input: str,
    context_wall_scenario_id: str,
    target_resolution_status: str,
    ui_expected_state: str,
    target_candidates: list[dict[str, Any]],
    requires_manager_or_clarification: bool,
    ambiguity_preserved: bool = False,
) -> dict[str, Any]:
    return _json_safe(
        {
            "scenario_id": scenario_id,
            "context_wall_scenario_id": context_wall_scenario_id,
            "raw_user_input": raw_user_input,
            "raw_user_input_role": "display_only",
            "semantic_owner": "fixture_manager_structured_decision",
            "manager_fixture_decision": _fixture_decision(
                target_resolution_status=target_resolution_status,
                requires_manager_or_clarification=requires_manager_or_clarification,
            ),
            "target_resolution_status": target_resolution_status,
            "requires_manager_or_clarification": requires_manager_or_clarification,
            "target_candidates_present": bool(target_candidates),
            "target_candidate_count": len(target_candidates),
            "target_candidates": list(target_candidates),
            "ambiguity_preserved": ambiguity_preserved,
            "ui_expected_state": ui_expected_state,
            "frontend_render_source": "backend_structured_context",
            "frontend_render_action": "render_candidates_or_ambiguity_only",
            "frontend_render_only": True,
            "frontend_selects_target": False,
            "frontend_infers_correction_intent": False,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_target": False,
            "deterministic_selected_intent": False,
            "deterministic_semantic_inference_used": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
        }
    )


def _scenarios() -> list[dict[str, Any]]:
    return [
        _scenario(
            scenario_id="remove_previous_item_ambiguous",
            context_wall_scenario_id="remove_tofu_multiple_targets",
            raw_user_input="\u628a\u525b\u525b\u90a3\u500b\u62ff\u6389",
            target_resolution_status="ambiguous",
            ui_expected_state="show_ambiguity",
            target_candidates=[
                _candidate("meal-item-001", "\u665a\u9910 / \u8c46\u5e72", action_affordance="remove"),
                _candidate("meal-item-002", "\u9ede\u5fc3 / \u8c46\u5e72", action_affordance="remove"),
            ],
            requires_manager_or_clarification=True,
            ambiguity_preserved=True,
        ),
        _scenario(
            scenario_id="remove_named_item_candidate",
            context_wall_scenario_id="remove_tofu_one_luwei",
            raw_user_input="\u8c46\u5e72\u62ff\u6389",
            target_resolution_status="candidate_supported",
            ui_expected_state="show_candidate_list",
            target_candidates=[
                _candidate("luwei-tofu-001", "\u6ef7\u5473 / \u8c46\u5e72", action_affordance="remove")
            ],
            requires_manager_or_clarification=False,
        ),
        _scenario(
            scenario_id="modify_drink_sugar_candidate",
            context_wall_scenario_id="half_sugar_one_prior_drink",
            raw_user_input="\u90a3\u676f\u6539\u534a\u7cd6",
            target_resolution_status="candidate_supported",
            ui_expected_state="show_candidate_list",
            target_candidates=[
                _candidate("drink-001", "\u5927\u676f\u73cd\u5976", action_affordance="correct")
            ],
            requires_manager_or_clarification=False,
        ),
        _scenario(
            scenario_id="modify_rice_portion_candidate",
            context_wall_scenario_id="long_session_less_rice",
            raw_user_input="\u98ef\u6539\u5c11\u4e00\u9ede",
            target_resolution_status="candidate_supported",
            ui_expected_state="show_candidate_list",
            target_candidates=[
                _candidate("dinner-rice-001", "\u665a\u9910 / \u767d\u98ef", action_affordance="correct")
            ],
            requires_manager_or_clarification=False,
        ),
        _scenario(
            scenario_id="correct_previous_identity_ambiguous",
            context_wall_scenario_id="half_sugar_multiple_drinks",
            raw_user_input="\u525b\u525b\u90a3\u500b\u5176\u5be6\u4e0d\u662f\u62ff\u9435",
            target_resolution_status="ambiguous",
            ui_expected_state="show_ambiguity",
            target_candidates=[
                _candidate("drink-001", "\u62ff\u9435", action_affordance="correct_identity"),
                _candidate("drink-002", "\u73cd\u5976", action_affordance="correct_identity"),
            ],
            requires_manager_or_clarification=True,
            ambiguity_preserved=True,
        ),
    ]


def _validate(
    scenarios: list[dict[str, Any]],
    *,
    context_wall_status: str,
    context_wall_scenarios: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    blockers: list[str] = []
    scenario_ids = [str(scenario.get("scenario_id") or "") for scenario in scenarios]
    if scenario_ids != list(_REQUIRED_SCENARIO_IDS):
        blockers.append("required_scenario_order_mismatch")
    if context_wall_status != "pass":
        blockers.append("context_conditioned_intent_wall_not_pass")
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "unknown")
        if scenario.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append(f"{scenario_id}.semantic_owner_not_fixture_manager")
        if scenario.get("frontend_render_source") != "backend_structured_context":
            blockers.append(f"{scenario_id}.frontend_not_rendering_backend_context")
        if scenario.get("frontend_render_only") is not True:
            blockers.append(f"{scenario_id}.frontend_not_render_only")
        if scenario.get("frontend_selects_target") is not False:
            blockers.append(f"{scenario_id}.frontend_selects_target")
        if scenario.get("frontend_infers_correction_intent") is not False:
            blockers.append(f"{scenario_id}.frontend_infers_correction_intent")
        if scenario.get("deterministic_selected_target") is not False:
            blockers.append(f"{scenario_id}.deterministic_selected_target")
        if scenario.get("deterministic_selected_intent") is not False:
            blockers.append(f"{scenario_id}.deterministic_selected_intent")
        if scenario.get("mutation_authority") is not False:
            blockers.append(f"{scenario_id}.mutation_authority")
        if scenario.get("manager_context_packet_schema_changed") is not False:
            blockers.append(f"{scenario_id}.manager_context_packet_schema_changed")
        context_wall_scenario_id = str(scenario.get("context_wall_scenario_id") or "")
        linked_context_wall_scenario = (
            (context_wall_scenarios or {}).get(context_wall_scenario_id)
            if context_wall_scenario_id
            else None
        )
        if context_wall_scenarios is not None:
            if linked_context_wall_scenario is None:
                blockers.append(f"{scenario_id}.context_wall_scenario_missing")
            elif linked_context_wall_scenario.get("target_candidate_count") is None:
                blockers.append(f"{scenario_id}.context_wall_candidate_count_missing")
        target_resolution_status = str(scenario.get("target_resolution_status") or "")
        target_candidate_count = int(scenario.get("target_candidate_count") or 0)
        if target_resolution_status == "candidate_supported":
            if scenario.get("target_candidates_present") is not True:
                blockers.append(f"{scenario_id}.candidate_target_missing")
            if target_candidate_count < 1:
                blockers.append(f"{scenario_id}.candidate_target_missing")
            if scenario.get("ui_expected_state") != "show_candidate_list":
                blockers.append(f"{scenario_id}.candidate_ui_state_wrong")
            if linked_context_wall_scenario is not None:
                context_wall_posture = str(
                    linked_context_wall_scenario.get("expected_semantic_posture") or ""
                )
                if context_wall_posture not in {
                    "correction_candidate_available",
                    "removal_candidate_available",
                }:
                    blockers.append(f"{scenario_id}.context_wall_posture_not_candidate")
                if int(linked_context_wall_scenario.get("target_candidate_count") or 0) < 1:
                    blockers.append(f"{scenario_id}.context_wall_candidate_missing")
        if target_resolution_status == "ambiguous":
            if scenario.get("ambiguity_preserved") is not True:
                blockers.append(f"{scenario_id}.ambiguity_not_preserved")
            if target_candidate_count < 2:
                blockers.append(f"{scenario_id}.ambiguous_candidates_too_low")
            if scenario.get("requires_manager_or_clarification") is not True:
                blockers.append(f"{scenario_id}.clarification_not_required")
            if scenario.get("ui_expected_state") != "show_ambiguity":
                blockers.append(f"{scenario_id}.ambiguity_ui_state_wrong")
            if linked_context_wall_scenario is not None:
                if linked_context_wall_scenario.get("expected_semantic_posture") != "ambiguous_target":
                    blockers.append(f"{scenario_id}.context_wall_posture_not_ambiguous")
                if linked_context_wall_scenario.get("ambiguity_preserved") is not True:
                    blockers.append(f"{scenario_id}.context_wall_ambiguity_not_preserved")
                if int(linked_context_wall_scenario.get("target_candidate_count") or 0) < 2:
                    blockers.append(f"{scenario_id}.context_wall_ambiguous_candidates_too_low")
    return blockers


def build_correction_removal_fixture_flow_artifact() -> dict[str, Any]:
    context_wall = build_context_conditioned_intent_wall_artifact()
    context_wall_status = str(context_wall.get("status") or "missing")
    context_wall_scenarios = {
        str(scenario.get("scenario_id") or ""): scenario
        for scenario in context_wall.get("scenarios", [])
        if isinstance(scenario, dict)
    }
    scenarios = _scenarios()
    blockers = _validate(
        scenarios,
        context_wall_status=context_wall_status,
        context_wall_scenarios=context_wall_scenarios,
    )
    candidate_scenarios = sum(
        1 for scenario in scenarios if scenario["target_resolution_status"] == "candidate_supported"
    )
    ambiguous_scenarios = sum(
        1 for scenario in scenarios if scenario["target_resolution_status"] == "ambiguous"
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_correction_removal_fixture_flow",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_correction_removal_fixture_flow",
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "context_conditioned_intent_wall_required": True,
            "context_conditioned_intent_wall_status": context_wall_status,
            "context_conditioned_intent_wall_scenario_links_valid": not blockers,
            "semantic_owner": "fixture_manager_structured_decision",
            "fixture_manager_used": True,
            "manager_fixture_semantic_source": "fixture_manager_structured_decision",
            "candidate_or_ambiguity_render_ready": not blockers,
            "frontend_render_only": True,
            "frontend_selects_target": False,
            "frontend_infers_correction_intent": False,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_target": False,
            "deterministic_selected_intent": False,
            "deterministic_semantic_inference_used": False,
            "mutation_authority": False,
            "mutation_changed": False,
            "runtime_truth_changed": False,
            "manager_context_packet_schema_changed": False,
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
                "scenario_count": len(scenarios),
                "candidate_supported_scenarios": candidate_scenarios,
                "ambiguous_scenarios": ambiguous_scenarios,
                "frontend_target_selection_scenarios": 0,
                "mutation_authority_scenarios": 0,
            },
            "scenarios": scenarios,
        }
    )
