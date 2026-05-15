from __future__ import annotations
from typing import Any

def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}

def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []

def _scenario_ids(payload: dict[str, Any]) -> set[str]:
    return {
        str(scenario.get("scenario_id") or "")
        for scenario in _list_value(payload.get("scenarios"))
        if isinstance(scenario, dict)
    }

def _scenario_count(payload: dict[str, Any], predicate) -> int:
    return sum(
        1
        for scenario in _list_value(payload.get("scenarios"))
        if isinstance(scenario, dict) and predicate(scenario)
    )

def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return _object_dict(payload.get("summary"))

def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0

def _coverage_entry(
    *,
    capability_id: str,
    label: str,
    intent_wall: bool,
    runtime_replay: bool,
    fake_provider: bool,
    evidence: list[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    intent_wall_required = capability_id not in {"forbidden_context_exclusion"}
    if not intent_wall and intent_wall_required:
        blockers.append(f"coverage.{capability_id}.missing_intent_wall")
    if not runtime_replay and capability_id not in {"query_no_mutation", "target_update_boundary"}:
        blockers.append(f"coverage.{capability_id}.missing_runtime_replay")
    if not fake_provider and capability_id in {
        "pending_followup_carryover",
        "correction_target_candidates",
        "removal_target_candidates",
        "ambiguity_preserved",
        "query_no_mutation",
        "target_update_boundary",
        "semantic_owner_boundary",
    }:
        blockers.append(f"coverage.{capability_id}.missing_fake_provider")
    if not intent_wall and intent_wall_required:
        coverage_status = "not_checked"
    elif intent_wall and runtime_replay and fake_provider:
        coverage_status = "fixture_runtime_and_fake_provider_checked"
    elif intent_wall and fake_provider:
        coverage_status = "fixture_and_fake_provider_checked"
    elif intent_wall and runtime_replay:
        coverage_status = "fixture_runtime_checked"
    elif runtime_replay and fake_provider:
        coverage_status = "runtime_and_fake_provider_checked"
    elif intent_wall:
        coverage_status = "fixture_checked"
    elif runtime_replay:
        coverage_status = "runtime_checked"
    elif fake_provider:
        coverage_status = "fake_provider_checked"
    else:
        coverage_status = "not_checked"
    return {
        "capability_id": capability_id,
        "label": label,
        "coverage_status": coverage_status,
        "intent_wall_checked": intent_wall,
        "runtime_replay_checked": runtime_replay,
        "fake_provider_checked": fake_provider,
        "evidence": evidence,
        "blockers": blockers,
    }

def build_context_coverage_matrix(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    wall = inputs["context_conditioned_intent_wall"]
    runtime = inputs["short_term_context_runtime_replay"]
    fake_provider = inputs["fake_provider_context_smoke"]
    quality = inputs["context_quality_pack"]
    wall_ids = _scenario_ids(wall)
    runtime_ids = _scenario_ids(runtime)
    fake_ids = _scenario_ids({"scenarios": fake_provider.get("manager_handoff_scenarios")})
    runtime_summary = _summary(runtime)
    quality_summary = _summary(quality)

    return {
        "pending_followup_carryover": _coverage_entry(
            capability_id="pending_followup_carryover",
            label="pending follow-up answer attaches to the active draft",
            intent_wall="luwei_pending_components_followup" in wall_ids,
            runtime_replay="pending_followup_answer" in runtime_ids,
            fake_provider="pending_followup_answer" in fake_ids,
            evidence=[
                "context wall: luwei_pending_components_followup",
                "runtime replay: pending_followup_answer",
                "fake provider: pending_followup_answer",
            ],
        ),
        "correction_target_candidates": _coverage_entry(
            capability_id="correction_target_candidates",
            label="correction utterances expose candidates without deterministic target selection",
            intent_wall={"half_sugar_one_prior_drink", "long_session_less_rice"}.issubset(wall_ids),
            runtime_replay={"modify_drink_sugar", "modify_rice_portion"}.issubset(runtime_ids),
            fake_provider="named_item_correction" in fake_ids,
            evidence=[
                "context wall: half_sugar_one_prior_drink, long_session_less_rice",
                "runtime replay: modify_drink_sugar, modify_rice_portion",
                "fake provider: named_item_correction",
            ],
        ),
        "removal_target_candidates": _coverage_entry(
            capability_id="removal_target_candidates",
            label="removal utterances expose candidates without deterministic target selection",
            intent_wall={"remove_tofu_one_luwei", "remove_tofu_multiple_targets"}.issubset(wall_ids),
            runtime_replay={"remove_previous_item", "remove_named_item"}.issubset(runtime_ids),
            fake_provider="named_item_correction" in fake_ids,
            evidence=[
                "context wall: remove_tofu_one_luwei, remove_tofu_multiple_targets",
                "runtime replay: remove_previous_item, remove_named_item",
                "fake provider: named_item_correction",
            ],
        ),
        "ambiguity_preserved": _coverage_entry(
            capability_id="ambiguity_preserved",
            label="ambiguous back references remain ambiguous for Manager review",
            intent_wall=_scenario_count(wall, lambda scenario: scenario.get("ambiguity_preserved") is True) >= 2,
            runtime_replay=_scenario_count(
                runtime,
                lambda scenario: scenario.get("expected_context_posture")
                == "ambiguous_until_manager_decision",
            )
            >= 2,
            fake_provider="ambiguous_back_reference" in fake_ids,
            evidence=[
                "context wall: ambiguity_preserved scenarios",
                "runtime replay: ambiguous_until_manager_decision scenarios",
                "fake provider: ambiguous_back_reference",
            ],
        ),
        "query_no_mutation": _coverage_entry(
            capability_id="query_no_mutation",
            label="query turns do not become mutation authority",
            intent_wall="previous_drink_calorie_query" in wall_ids,
            runtime_replay=False,
            fake_provider="previous_drink_calorie_query" in fake_ids,
            evidence=[
                "context wall: previous_drink_calorie_query",
                "fake provider: previous_drink_calorie_query",
            ],
        ),
        "target_update_boundary": _coverage_entry(
            capability_id="target_update_boundary",
            label="daily target update requires explicit Manager structured decision",
            intent_wall="explicit_daily_target_1800" in wall_ids
            and "meal_estimate_800_not_target" in wall_ids,
            runtime_replay=False,
            fake_provider={"explicit_daily_target_1800", "meal_estimate_800_not_target"}.issubset(fake_ids),
            evidence=[
                "context wall: explicit_daily_target_1800 vs meal_estimate_800_not_target",
                "fake provider: explicit_daily_target_1800, meal_estimate_800_not_target",
            ],
        ),
        "long_session_bounded_context": _coverage_entry(
            capability_id="long_session_bounded_context",
            label="long sessions keep bounded recent context and hard-pinned targets",
            intent_wall="long_session_less_rice" in wall_ids,
            runtime_replay="long_chat_with_pinned_pending_draft" in runtime_ids
            and _int_value(runtime_summary.get("pending_pin_scenarios")) >= 1,
            fake_provider=False,
            evidence=[
                "context wall: long_session_less_rice",
                "runtime replay: long_chat_with_pinned_pending_draft",
            ],
        ),
        "forbidden_context_exclusion": _coverage_entry(
            capability_id="forbidden_context_exclusion",
            label="forbidden debug/raw/long-term/proactive context stays excluded",
            intent_wall=False,
            runtime_replay=_scenario_count(
                runtime,
                lambda scenario: scenario.get("forbidden_context_detected") is True,
            )
            == 0,
            fake_provider=bool(
                _object_dict(fake_provider.get("provider_input_summary")).get(
                    "forbidden_context_excluded"
                )
            ),
            evidence=[
                "runtime replay: forbidden_context_detected false",
                "fake provider: forbidden_context_excluded true",
            ],
        ),
        "semantic_owner_boundary": _coverage_entry(
            capability_id="semantic_owner_boundary",
            label="semantic decision source remains fixture Manager, not deterministic/frontend code",
            intent_wall=wall.get("manager_fixture_semantic_source_used") is True,
            runtime_replay=runtime.get("deterministic_semantic_inference_used") is False,
            fake_provider=fake_provider.get("final_semantic_decision_source")
            == "fixture_manager_structured_decision"
            and _int_value(quality_summary.get("fake_provider_handoff_scenario_count")) >= 6,
            evidence=[
                "context wall: manager_fixture_semantic_source_used",
                "runtime replay: deterministic_semantic_inference_used false",
                "fake provider: fixture_manager_structured_decision",
            ],
        ),
    }
