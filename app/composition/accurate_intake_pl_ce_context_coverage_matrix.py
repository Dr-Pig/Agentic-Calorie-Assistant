from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

REQUIRED_INPUTS = (
    "context_conditioned_intent_wall",
    "short_term_context_runtime_replay",
    "fake_provider_context_smoke",
    "context_quality_pack",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_conditioned_intent_wall": "accurate_intake_context_conditioned_intent_wall",
    "short_term_context_runtime_replay": "accurate_intake_short_term_context_runtime_replay",
    "fake_provider_context_smoke": "accurate_intake_fake_provider_context_smoke",
    "context_quality_pack": "accurate_intake_context_quality_pack",
}

EXPECTED_STATUSES = {
    "context_conditioned_intent_wall": {"pass"},
    "short_term_context_runtime_replay": {
        "runtime_replay_diagnostic_pass",
        "diagnostic_has_known_context_gaps",
    },
    "fake_provider_context_smoke": {"pass"},
    "context_quality_pack": {"context_quality_diagnostic_pass"},
}

FORBIDDEN_TRUTHY_FLAGS = (
    "context_engineering_fault_claimed",
    "manager_context_packet_schema_changed",
    "deterministic_selected_target",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "live_websearch_used",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "runtime_truth_changed",
    "mutation_changed",
    "writes_performed",
    "import_allowed",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "canonical_eval_promoted",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "none", "null", "not_available", "not_checked"}
    return True


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


def _input_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") == "missing":
        return [f"{group_id}.missing"]
    if payload.get("artifact_type") == "invalid_json":
        return [f"{group_id}.invalid_json"]
    if payload.get("artifact_type") == "invalid_json_shape":
        return [f"{group_id}.invalid_json_shape"]
    expected_type = EXPECTED_ARTIFACT_TYPES[group_id]
    if payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    if _status(payload) not in EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{payload.get('status')}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(payload.get(flag)):
            blockers.append(f"{group_id}.{flag}")
    blockers.extend(_nested_forbidden_claim_blockers(group_id, payload))
    blockers.extend(_upstream_invariant_blockers(group_id, payload))
    return list(dict.fromkeys(blockers))


def _nested_forbidden_claim_blockers(group_id: str, value: Any, path: str = "") -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_TRUTHY_FLAGS and _claim_is_true(nested_value):
                blockers.append(f"{group_id}.{nested_path}")
            blockers.extend(_nested_forbidden_claim_blockers(group_id, nested_value, nested_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            nested_path = f"{path}[{index}]"
            blockers.extend(_nested_forbidden_claim_blockers(group_id, item, nested_path))
    return list(dict.fromkeys(blockers))


def _upstream_invariant_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _summary(payload)
    if group_id == "context_conditioned_intent_wall":
        if _int_value(summary.get("scenario_count")) < 11:
            blockers.append(f"{group_id}.scenario_count_too_low")
        if payload.get("manager_fixture_semantic_source_used") is not True:
            blockers.append(f"{group_id}.fixture_manager_semantic_source_missing")
    elif group_id == "short_term_context_runtime_replay":
        if payload.get("runtime_trace_backed") is not True:
            blockers.append(f"{group_id}.runtime_trace_backed_not_true")
        if _int_value(payload.get("scenario_count")) < 7:
            blockers.append(f"{group_id}.scenario_count_too_low")
    elif group_id == "fake_provider_context_smoke":
        if payload.get("manager_handoff_matrix_checked") is not True:
            blockers.append(f"{group_id}.manager_handoff_matrix_missing")
        if _int_value(summary.get("manager_handoff_scenario_count")) < 3:
            blockers.append(f"{group_id}.manager_handoff_scenario_count_too_low")
        if _int_value(summary.get("ambiguous_back_reference_scenarios")) < 1:
            blockers.append(f"{group_id}.ambiguous_back_reference_missing")
    elif group_id == "context_quality_pack":
        if payload.get("short_term_context_runtime_replay_checked") is not True:
            blockers.append(f"{group_id}.runtime_replay_not_checked")
        if _int_value(summary.get("short_term_runtime_replay_scenario_count")) < 7:
            blockers.append(f"{group_id}.short_term_runtime_replay_scenario_count_too_low")
        if _int_value(summary.get("fake_provider_handoff_scenario_count")) < 3:
            blockers.append(f"{group_id}.fake_provider_handoff_scenario_count_too_low")
    return blockers


def _input_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": payload.get("status") or "not_available",
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


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
    if not intent_wall and capability_id not in {"forbidden_context_exclusion"}:
        blockers.append(f"coverage.{capability_id}.missing_intent_wall")
    if not runtime_replay and capability_id not in {"query_no_mutation", "target_update_boundary"}:
        blockers.append(f"coverage.{capability_id}.missing_runtime_replay")
    if not fake_provider and capability_id in {
        "pending_followup_carryover",
        "correction_target_candidates",
        "removal_target_candidates",
        "ambiguity_preserved",
        "semantic_owner_boundary",
    }:
        blockers.append(f"coverage.{capability_id}.missing_fake_provider")
    if intent_wall and runtime_replay and fake_provider:
        coverage_status = "fixture_runtime_and_fake_provider_checked"
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


def _build_matrix(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
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
            fake_provider=False,
            evidence=["context wall: previous_drink_calorie_query"],
        ),
        "target_update_boundary": _coverage_entry(
            capability_id="target_update_boundary",
            label="daily target update requires explicit Manager structured decision",
            intent_wall="explicit_daily_target_1800" in wall_ids
            and "meal_estimate_800_not_target" in wall_ids,
            runtime_replay=False,
            fake_provider=False,
            evidence=["context wall: explicit_daily_target_1800 vs meal_estimate_800_not_target"],
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
            and _int_value(quality_summary.get("fake_provider_handoff_scenario_count")) >= 3,
            evidence=[
                "context wall: manager_fixture_semantic_source_used",
                "runtime replay: deterministic_semantic_inference_used false",
                "fake provider: fixture_manager_structured_decision",
            ],
        ),
    }


def build_pl_ce_context_coverage_matrix_artifact(
    *,
    context_conditioned_intent_wall: dict[str, Any],
    short_term_context_runtime_replay: dict[str, Any],
    fake_provider_context_smoke: dict[str, Any],
    context_quality_pack: dict[str, Any],
) -> dict[str, Any]:
    inputs = {
        "context_conditioned_intent_wall": _object_dict(context_conditioned_intent_wall),
        "short_term_context_runtime_replay": _object_dict(short_term_context_runtime_replay),
        "fake_provider_context_smoke": _object_dict(fake_provider_context_smoke),
        "context_quality_pack": _object_dict(context_quality_pack),
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_input_blockers(group_id, payload))
    matrix = _build_matrix(inputs)
    for entry in matrix.values():
        blockers.extend(entry["blockers"])
    blockers = list(dict.fromkeys(blockers))

    runtime_summary = _summary(inputs["short_term_context_runtime_replay"])
    known_gap_signals = list(runtime_summary.get("known_gap_signals") or [])
    known_runtime_gap_count = _int_value(runtime_summary.get("current_gap_scenarios"))
    if (
        inputs["short_term_context_runtime_replay"].get("status")
        == "diagnostic_has_known_context_gaps"
        or known_gap_signals
    ) and known_runtime_gap_count == 0:
        known_runtime_gap_count = max(1, len(known_gap_signals))
    if blockers:
        status = "blocked"
    elif known_runtime_gap_count:
        status = "context_coverage_matrix_ready_with_known_runtime_gaps"
    else:
        status = "context_coverage_matrix_ready_for_human_review"
    covered_capability_count = sum(
        1 for entry in matrix.values() if entry["coverage_status"] != "not_checked"
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
            "claim_scope": "pl_ce_short_term_context_coverage_matrix_for_human_review",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "status": status,
            "blockers": blockers,
            "input_statuses": _input_statuses(inputs),
            "coverage_matrix": matrix,
            "summary": {
                "capability_count": len(matrix),
                "covered_capability_count": covered_capability_count,
                "known_runtime_gap_count": known_runtime_gap_count,
                "blocked_capability_count": sum(1 for entry in matrix.values() if entry["blockers"]),
            },
            "known_runtime_gap_signals": known_gap_signals,
            "autofix_attempted": False,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "human_review_required": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_STATUSES",
    "REQUIRED_INPUTS",
    "build_pl_ce_context_coverage_matrix_artifact",
]
