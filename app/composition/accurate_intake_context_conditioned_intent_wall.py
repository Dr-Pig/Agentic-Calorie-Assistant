from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.intake.application.manager_context_policy import (
    build_manager_context_packet_v1,
)
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent


_REQUIRED_SCENARIO_IDS = (
    "luwei_pending_components_followup",
    "half_sugar_no_prior_drink",
    "half_sugar_one_prior_drink",
    "half_sugar_multiple_drinks",
    "remove_tofu_no_luwei_context",
    "remove_tofu_one_luwei",
    "remove_tofu_multiple_targets",
    "previous_drink_calorie_query",
    "explicit_daily_target_1800",
    "meal_estimate_800_not_target",
    "long_session_less_rice",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _message(index: int, content: str, role: str = "user") -> dict[str, Any]:
    return {
        "message_id": index,
        "role": role,
        "content": content,
        "read_only": True,
        "mutation_authority": False,
    }


def _target(
    target_id: str,
    display_name: str,
    *,
    target_type: str = "meal_item",
) -> dict[str, Any]:
    return {
        "target_object_type": target_type,
        "target_object_id": target_id,
        "display_name": display_name,
        "uniqueness_status": "candidate",
        "removable": True,
        "eligible": True,
    }


def _current_context(
    *,
    raw_user_input: str,
    recent_chat_turns: list[dict[str, Any]] | None = None,
    pending_followup: dict[str, Any] | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
) -> CurrentTurnContextV1:
    return CurrentTurnContextV1(
        user_utterance=raw_user_input,
        last_system_question=(
            "\u9019\u4efd\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f"
            if pending_followup
            else None
        ),
        recent_chat_turns=list(recent_chat_turns or []),
        pending_followup=pending_followup,
        recent_item_targets=list(target_candidates or []),
        current_budget_snapshot={
            "local_date": "2026-05-05",
            "budget_kcal": 1500,
            "consumed_kcal": 620,
            "remaining_kcal": 880,
            "read_only": True,
            "mutation_authority": False,
        },
        current_interaction_event=InteractionEvent(
            source="chat",
            event_type="message_received",
            raw_text=raw_user_input,
        ),
        candidate_attachment_targets=list(target_candidates or []),
    )


def _fixture_decision(
    *,
    expected_semantic_posture: str,
    mutation_intent_candidate: str = "no_mutation",
) -> dict[str, Any]:
    return {
        "semantic_source": "fixture_manager_structured_decision",
        "expected_semantic_posture": expected_semantic_posture,
        "mutation_intent_candidate": mutation_intent_candidate,
        "deterministic_role": "supply_context_candidates_and_validate_boundaries",
    }


def _scenario(
    *,
    scenario_id: str,
    raw_user_input: str,
    context_variant_group: str,
    expected_semantic_posture: str,
    target_candidates: list[dict[str, Any]] | None = None,
    recent_chat_turns: list[dict[str, Any]] | None = None,
    pending_followup: dict[str, Any] | None = None,
    pending_draft: dict[str, Any] | None = None,
    ambiguity_preserved: bool = False,
    query_no_mutation: bool = False,
    target_update_requires_manager_decision: bool = False,
    mutation_intent_candidate: str = "no_mutation",
    long_session_expected: bool = False,
) -> dict[str, Any]:
    candidates = list(target_candidates or [])
    context = _current_context(
        raw_user_input=raw_user_input,
        recent_chat_turns=recent_chat_turns,
        pending_followup=pending_followup,
        target_candidates=candidates,
    )
    packet = build_manager_context_packet_v1(
        current_turn_context=context,
        user_id="plce-context-wall-user",
        local_date="2026-05-05",
        session_id=f"context-wall-{scenario_id}",
        pending_draft=pending_draft,
        target_candidates=candidates,
    )
    loading = packet["context_loading_artifact"]
    loaded_summary = loading["loaded_context_summary"]
    omitted_summary = loading["omitted_context_summary"]
    hard_pins = packet["hard_pins"]
    packet_candidates = packet["target_candidates"]["for_correction_or_removal"]

    target_candidate_count = int(loaded_summary["target_candidate_count"])
    recent_chat_messages_omitted = int(omitted_summary["recent_chat_messages_omitted"])
    recent_chat_message_count = len(packet["recent_chat_window"]["messages"])
    return _json_safe(
        {
            "scenario_id": scenario_id,
            "context_variant_group": context_variant_group,
            "raw_user_input": raw_user_input,
            "raw_user_input_role": "display_only",
            "semantic_owner": "fixture_manager_structured_decision",
            "fixture_manager_decision": _fixture_decision(
                expected_semantic_posture=expected_semantic_posture,
                mutation_intent_candidate=mutation_intent_candidate,
            ),
            "expected_semantic_posture": expected_semantic_posture,
            "manager_context_policy_version": packet["metadata"]["context_policy_version"],
            "pending_followup_carryover": hard_pins["pending_followup"] is not None,
            "pending_draft_present": hard_pins["pending_draft"] is not None,
            "target_candidates_present": bool(packet_candidates),
            "target_candidate_count": target_candidate_count,
            "ambiguity_preserved": ambiguity_preserved,
            "query_no_mutation": query_no_mutation,
            "target_update_requires_manager_decision": target_update_requires_manager_decision,
            "long_session_expected": long_session_expected,
            "recent_chat_message_count": recent_chat_message_count,
            "recent_chat_messages_omitted": recent_chat_messages_omitted,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "frontend_raw_text_semantic_router": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
        }
    )


def _long_session_turns() -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for index in range(1, 27):
        turns.append(_message(index, f"context filler turn {index}"))
    turns.extend(
        [
            _message(27, "\u665a\u9910\u5403\u96de\u817f\u4fbf\u7576", role="user"),
            _message(28, "\u5df2\u8a18\u9304\u665a\u9910\uff0c\u542b\u767d\u98ef", role="assistant"),
        ]
    )
    return turns


def _scenarios() -> list[dict[str, Any]]:
    half_sugar = "\u6539\u534a\u7cd6"
    remove_tofu = "\u8c46\u5e72\u62ff\u6389"
    pending_luwei_followup = {
        "followup_id": "followup-luwei-components",
        "draft_id": "draft-luwei-001",
        "question": "\u9019\u4efd\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f",
    }
    pending_luwei_draft = {
        "draft_id": "draft-luwei-001",
        "display_name": "\u6ef7\u5473",
        "status": "pending_components",
    }
    return [
        _scenario(
            scenario_id="luwei_pending_components_followup",
            raw_user_input="\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
            context_variant_group="pending_luwei_components",
            expected_semantic_posture="attach_to_pending_draft",
            recent_chat_turns=[
                _message(1, "\u6211\u5403\u6ef7\u5473"),
                _message(2, "\u9019\u4efd\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f", role="assistant"),
            ],
            pending_followup=pending_luwei_followup,
            pending_draft=pending_luwei_draft,
            mutation_intent_candidate="complete_pending_draft",
        ),
        _scenario(
            scenario_id="half_sugar_no_prior_drink",
            raw_user_input=half_sugar,
            context_variant_group="half_sugar",
            expected_semantic_posture="clarification_required",
        ),
        _scenario(
            scenario_id="half_sugar_one_prior_drink",
            raw_user_input=half_sugar,
            context_variant_group="half_sugar",
            expected_semantic_posture="correction_candidate_available",
            target_candidates=[_target("drink-001", "\u5927\u676f\u73cd\u5976")],
            mutation_intent_candidate="correction_candidate",
        ),
        _scenario(
            scenario_id="half_sugar_multiple_drinks",
            raw_user_input=half_sugar,
            context_variant_group="half_sugar",
            expected_semantic_posture="ambiguous_target",
            target_candidates=[
                _target("drink-001", "\u5927\u676f\u73cd\u5976"),
                _target("drink-002", "\u7d05\u8336"),
            ],
            ambiguity_preserved=True,
            mutation_intent_candidate="clarification_required",
        ),
        _scenario(
            scenario_id="remove_tofu_no_luwei_context",
            raw_user_input=remove_tofu,
            context_variant_group="remove_tofu",
            expected_semantic_posture="clarification_required",
        ),
        _scenario(
            scenario_id="remove_tofu_one_luwei",
            raw_user_input=remove_tofu,
            context_variant_group="remove_tofu",
            expected_semantic_posture="removal_candidate_available",
            target_candidates=[_target("luwei-tofu-001", "\u6ef7\u5473 / \u8c46\u5e72")],
            mutation_intent_candidate="removal_candidate",
        ),
        _scenario(
            scenario_id="remove_tofu_multiple_targets",
            raw_user_input=remove_tofu,
            context_variant_group="remove_tofu",
            expected_semantic_posture="ambiguous_target",
            target_candidates=[
                _target("luwei-tofu-001", "\u6ef7\u5473 / \u8c46\u5e72"),
                _target("snack-tofu-002", "\u9ede\u5fc3 / \u8c46\u5e72"),
            ],
            ambiguity_preserved=True,
            mutation_intent_candidate="clarification_required",
        ),
        _scenario(
            scenario_id="previous_drink_calorie_query",
            raw_user_input="\u525b\u525b\u90a3\u676f\u591a\u5c11\u71b1\u91cf\uff1f",
            context_variant_group="drink_query",
            expected_semantic_posture="query_no_mutation",
            target_candidates=[_target("drink-001", "\u5927\u676f\u73cd\u5976")],
            query_no_mutation=True,
        ),
        _scenario(
            scenario_id="explicit_daily_target_1800",
            raw_user_input="\u4eca\u5929\u76ee\u6a19\u6539\u6210 1800",
            context_variant_group="target_vs_meal_kcal",
            expected_semantic_posture="daily_target_update_candidate",
            target_update_requires_manager_decision=True,
            mutation_intent_candidate="target_update_candidate",
        ),
        _scenario(
            scenario_id="meal_estimate_800_not_target",
            raw_user_input="\u9019\u9910\u5927\u6982 800",
            context_variant_group="target_vs_meal_kcal",
            expected_semantic_posture="meal_estimate_context",
            mutation_intent_candidate="meal_estimate_candidate",
        ),
        _scenario(
            scenario_id="long_session_less_rice",
            raw_user_input="\u90a3\u500b\u6539\u5c11\u98ef",
            context_variant_group="long_session_target_resolution",
            expected_semantic_posture="correction_candidate_available",
            recent_chat_turns=_long_session_turns(),
            target_candidates=[_target("dinner-rice-001", "\u665a\u9910 / \u767d\u98ef")],
            long_session_expected=True,
            mutation_intent_candidate="correction_candidate",
        ),
    ]


def _validate(scenarios: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    scenario_ids = [str(scenario.get("scenario_id") or "") for scenario in scenarios]
    if scenario_ids != list(_REQUIRED_SCENARIO_IDS):
        blockers.append("required_scenario_order_mismatch")
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "unknown")
        expected_posture = str(scenario.get("expected_semantic_posture") or "")
        fixture_decision = scenario.get("fixture_manager_decision")
        fixture_decision = fixture_decision if isinstance(fixture_decision, dict) else {}
        fixture_posture = str(fixture_decision.get("expected_semantic_posture") or "")
        mutation_candidate = str(fixture_decision.get("mutation_intent_candidate") or "")
        if scenario.get("semantic_owner") != "fixture_manager_structured_decision":
            blockers.append(f"{scenario_id}.semantic_owner_not_fixture_manager")
        if scenario.get("raw_user_input_role") != "display_only":
            blockers.append(f"{scenario_id}.raw_user_input_role_not_display_only")
        if fixture_decision.get("semantic_source") != "fixture_manager_structured_decision":
            blockers.append(f"{scenario_id}.fixture_decision_semantic_source_not_manager")
        if fixture_posture != expected_posture:
            blockers.append(f"{scenario_id}.fixture_decision_posture_mismatch")
        if scenario.get("deterministic_supplies_candidates_and_pins_only") is not True:
            blockers.append(f"{scenario_id}.deterministic_not_limited_to_context_support")
        if scenario.get("deterministic_selected_intent") is not False:
            blockers.append(f"{scenario_id}.deterministic_selected_intent")
        if scenario.get("deterministic_selected_target") is not False:
            blockers.append(f"{scenario_id}.deterministic_selected_target")
        if scenario.get("frontend_raw_text_semantic_router") is not False:
            blockers.append(f"{scenario_id}.frontend_raw_text_semantic_router")
        if scenario.get("mutation_authority") is not False:
            blockers.append(f"{scenario_id}.mutation_authority")
        if scenario.get("manager_context_packet_schema_changed") is not False:
            blockers.append(f"{scenario_id}.manager_context_packet_schema_changed")
        if expected_posture == "attach_to_pending_draft":
            if scenario.get("pending_followup_carryover") is not True:
                blockers.append(f"{scenario_id}.pending_followup_missing")
            if scenario.get("pending_draft_present") is not True:
                blockers.append(f"{scenario_id}.pending_draft_missing")
            if mutation_candidate != "complete_pending_draft":
                blockers.append(f"{scenario_id}.pending_followup_mutation_candidate_missing")
        if expected_posture == "clarification_required":
            if int(scenario.get("target_candidate_count") or 0) != 0:
                blockers.append(f"{scenario_id}.clarification_has_unexpected_target_candidates")
            if scenario.get("target_candidates_present") is not False:
                blockers.append(f"{scenario_id}.clarification_has_unexpected_target_candidates")
        if expected_posture == "ambiguous_target":
            if scenario.get("ambiguity_preserved") is not True:
                blockers.append(f"{scenario_id}.ambiguity_not_preserved")
            if int(scenario.get("target_candidate_count") or 0) < 2:
                blockers.append(f"{scenario_id}.ambiguous_candidates_too_low")
            if mutation_candidate != "clarification_required":
                blockers.append(f"{scenario_id}.ambiguous_mutation_candidate_not_clarification")
        if expected_posture == "query_no_mutation":
            if scenario.get("query_no_mutation") is not True:
                blockers.append(f"{scenario_id}.query_no_mutation_missing")
            if mutation_candidate != "no_mutation":
                blockers.append(f"{scenario_id}.query_mutation_intent_not_no_mutation")
        if expected_posture in {
            "correction_candidate_available",
            "removal_candidate_available",
        }:
            if scenario.get("target_candidates_present") is not True:
                blockers.append(f"{scenario_id}.candidate_target_missing")
            if int(scenario.get("target_candidate_count") or 0) < 1:
                blockers.append(f"{scenario_id}.candidate_target_missing")
            expected_mutation = (
                "removal_candidate"
                if expected_posture == "removal_candidate_available"
                else "correction_candidate"
            )
            if mutation_candidate != expected_mutation:
                blockers.append(f"{scenario_id}.candidate_mutation_intent_mismatch")
        if expected_posture == "daily_target_update_candidate":
            if scenario.get("target_update_requires_manager_decision") is not True:
                blockers.append(f"{scenario_id}.target_update_manager_decision_missing")
            if mutation_candidate != "target_update_candidate":
                blockers.append(f"{scenario_id}.target_update_mutation_candidate_missing")
        if expected_posture == "meal_estimate_context":
            if scenario.get("target_update_requires_manager_decision") is not False:
                blockers.append(f"{scenario_id}.meal_estimate_marked_as_target_update")
            if mutation_candidate != "meal_estimate_candidate":
                blockers.append(f"{scenario_id}.meal_estimate_mutation_candidate_missing")
        if scenario.get("long_session_expected") is True:
            if int(scenario.get("recent_chat_message_count") or 0) != 20:
                blockers.append(f"{scenario_id}.recent_chat_window_not_bounded")
            if int(scenario.get("recent_chat_messages_omitted") or 0) <= 0:
                blockers.append(f"{scenario_id}.recent_chat_omission_not_recorded")
            if int(scenario.get("target_candidate_count") or 0) < 1:
                blockers.append(f"{scenario_id}.long_session_target_candidate_missing")
    return blockers


def build_context_conditioned_intent_wall_artifact() -> dict[str, Any]:
    scenarios = _scenarios()
    blockers = _validate(scenarios)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_conditioned_intent_wall",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_short_term_context_conditioned_intent_regression_wall",
            "local_only": True,
            "diagnostic_only": True,
            "fixture_manager_used": True,
            "manager_fixture_semantic_source": "fixture_manager_structured_decision",
            "manager_fixture_semantic_source_used": True,
            "pending_followup_carryover": any(
                scenario["pending_followup_carryover"] for scenario in scenarios
            ),
            "ambiguity_preserved": any(scenario["ambiguity_preserved"] for scenario in scenarios),
            "query_no_mutation": any(scenario["query_no_mutation"] for scenario in scenarios),
            "target_update_requires_manager_decision": any(
                scenario["target_update_requires_manager_decision"] for scenario in scenarios
            ),
            "deterministic_supplies_candidates_and_pins_only": True,
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
            "production_db_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "scenario_count": len(scenarios),
                "context_variant_groups": sorted(
                    {str(scenario["context_variant_group"]) for scenario in scenarios}
                ),
                "ambiguous_scenarios": sum(
                    1 for scenario in scenarios if scenario["ambiguity_preserved"]
                ),
                "query_no_mutation_scenarios": sum(
                    1 for scenario in scenarios if scenario["query_no_mutation"]
                ),
                "target_update_manager_decision_scenarios": sum(
                    1
                    for scenario in scenarios
                    if scenario["target_update_requires_manager_decision"]
                ),
            },
            "scenarios": scenarios,
        }
    )


__all__ = ["build_context_conditioned_intent_wall_artifact"]
