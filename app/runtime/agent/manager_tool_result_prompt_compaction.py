from __future__ import annotations

import json
from typing import Any

from app.runtime.agent.manager_tool_result_visibility import nutrition_payload_values_must_be_hidden

_NUTRITION_PAYLOAD_PROMPT_FIELDS = (
    "meal_title",
    "estimated_kcal",
    "route_target",
    "action_taken",
    "followup_question",
    "reply_text",
    "unresolved_info",
)
_TRACE_CONTRACT_PROMPT_FIELDS = (
    "route_family",
    "source_basis",
    "user_provided_kcal",
    "shadow_stub",
    "db_hit_type",
    "match_confidence",
    "response_mode_hint",
    "reason_not_direct_answer",
    "unresolved_info",
    "missing_slots",
    "blocking_slots",
    "canonical_write_decision",
    "approved_user_provided_kcal_trace",
    "macro_display_authorized",
    "macro_visibility_status",
    "macro_guard_reason",
    "optional_refinement_allowed",
    "optional_refinement_targets",
    "optional_refinement_question",
    "grounding_summary",
    "why_not_exact",
    "search_attempt_count",
    "search_query",
    "correction_target_ref",
    "correction_operation",
    "intake_execution_guard_family",
    "best_estimate_mode",
    "estimate_confidence_tier",
)
_CORRECTION_TARGET_PROMPT_FIELDS = (
    "meal_thread_id",
    "meal_item_id",
    "canonical_name",
    "observed_canonical_name",
    "operation",
    "correction_operation",
    "target_resolution_source",
    "correction_confidence",
    "manager_target_proposal_validation",
)
_BUDGET_SUMMARY_PROMPT_FIELDS = (
    "budget_kcal",
    "consumed_kcal_before",
    "predicted_consumed_kcal_after",
    "predicted_remaining_kcal_after",
    "overshoot_detected",
    "overshoot_kcal",
    "replaced_kcal_before",
)
_LATEST_WEIGHT_OBSERVATION_PROMPT_FIELDS = ("observation_id", "value", "unit", "local_date")
_RECORDED_BODY_OBSERVATION_PROMPT_FIELDS = (
    "observation_id",
    "observation_type",
    "value",
    "unit",
    "local_date",
)
_MUTATION_RESULT_PROMPT_FIELDS = (
    "status",
    "body_observation_recorded",
    "body_plan_mutated",
    "ledger_mutated",
)


def compact_tool_results_prompt_payload(tool_results: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_results, list):
        return []
    return [_compact_tool_result_prompt_payload(item) for item in tool_results if isinstance(item, dict)]


def _compact_tool_result_prompt_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "prompt_payload_kind": "manager_tool_result_prompt_compact",
        "tool_name": tool_result.get("tool_name") or tool_result.get("name"),
        "confidence": tool_result.get("confidence"),
        "failure_family": tool_result.get("failure_family"),
    }
    if tool_result.get("error_message"):
        compact["error_message"] = tool_result.get("error_message")
    evidence = _object_mapping(tool_result.get("evidence"))
    if evidence:
        compact["evidence"] = _compact_tool_evidence_prompt_payload(evidence)
    provenance = _object_mapping(tool_result.get("provenance"))
    if provenance:
        compact["provenance"] = _compact_tool_provenance_prompt_payload(provenance)
    mutation_result = _object_mapping(tool_result.get("mutation_result"))
    if mutation_result:
        compact["mutation_result"] = _select_prompt_fields(mutation_result, _MUTATION_RESULT_PROMPT_FIELDS)
    return {key: value for key, value in compact.items() if value not in (None, "", {}, [])}


def _compact_tool_evidence_prompt_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    nutrition_payload = _object_mapping(evidence.get("nutrition_payload"))
    if nutrition_payload:
        compact["nutrition_payload"] = _compact_nutrition_payload_prompt_payload(nutrition_payload)
    target_evidence_payload = _object_mapping(evidence.get("target_evidence_payload"))
    if target_evidence_payload:
        compact["target_evidence_payload"] = target_evidence_payload
    if evidence.get("latest_weight_status") not in (None, ""):
        compact["latest_weight_status"] = _json_safe(evidence["latest_weight_status"])
    latest_weight = _object_mapping(evidence.get("latest_weight_observation"))
    if latest_weight:
        compact["latest_weight_observation"] = _select_prompt_fields(
            latest_weight, _LATEST_WEIGHT_OBSERVATION_PROMPT_FIELDS
        )
    recorded = _object_mapping(evidence.get("recorded_body_observation"))
    if recorded:
        compact["recorded_body_observation"] = _select_prompt_fields(
            recorded, _RECORDED_BODY_OBSERVATION_PROMPT_FIELDS
        )
    return compact


def _compact_nutrition_payload_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    trace_contract = _object_mapping(payload.get("trace_contract"))
    fields = _NUTRITION_PAYLOAD_PROMPT_FIELDS
    if nutrition_payload_values_must_be_hidden(trace_contract):
        fields = tuple(field for field in fields if field not in {"estimated_kcal", "reply_text"})
    compact = _select_prompt_fields(payload, fields)
    if nutrition_payload_values_must_be_hidden(trace_contract):
        compact["disallowed_fact_policy"] = "nutrition_payload_values_hidden_until_commit_eligible"
    if trace_contract:
        compact["trace_contract"] = _select_prompt_fields(trace_contract, _TRACE_CONTRACT_PROMPT_FIELDS)
    return compact


def _compact_tool_provenance_prompt_payload(provenance: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in ("canonical_tool_name", "truth_owner", "tool_kind", "mutation_authority"):
        if key in provenance and provenance.get(key) not in (None, ""):
            compact[key] = _json_safe(provenance[key])
    correction_target = _select_prompt_fields(
        _object_mapping(provenance.get("correction_target")), _CORRECTION_TARGET_PROMPT_FIELDS
    )
    if correction_target:
        compact["correction_target"] = correction_target
    budget_summary = _select_prompt_fields(
        _object_mapping(provenance.get("budget_summary")), _BUDGET_SUMMARY_PROMPT_FIELDS
    )
    if budget_summary:
        compact["budget_summary"] = budget_summary
    for key in ("macro_summary", "evidence_summary"):
        value = provenance.get(key)
        if value not in (None, "", {}, []):
            compact[key] = _json_safe(value)
    return compact


def _select_prompt_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: _json_safe(payload[key]) for key in fields if payload.get(key) not in (None, "", {}, [])}


def _object_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    safe = _json_safe(value)
    return dict(safe) if isinstance(safe, dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


__all__ = ["compact_tool_results_prompt_payload"]
