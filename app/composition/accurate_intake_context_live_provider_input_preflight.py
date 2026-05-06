from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_context_live_diagnostic_case_matrix_artifact,
)


RESPONSE_SCHEMA_NAME = "accurate_intake_context_live_manager_decision_v1"
REQUIRED_RESPONSE_FIELDS = (
    "case_id",
    "manager_intent",
    "workflow_effect",
    "target_resolution",
    "mutation_request",
    "clarification_question",
    "confidence_notes",
)
FORBIDDEN_INPUT_KEYS = (
    "raw_trace_dump",
    "dogfood_review_artifact",
    "fooddb_gap_candidate_as_truth",
    "long_term_memory",
    "debug_artifact",
)
FORBIDDEN_TRUTHY_FLAGS = (
    "live_llm_invoked",
    "live_provider_invoked",
    "fooddb_used",
    "web_tavily_used",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "product_readiness_claimed",
    "private_self_use_approved",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _case_id(case: dict[str, Any]) -> str:
    return str(case.get("case_id") or "")


def _response_schema() -> dict[str, Any]:
    return {
        "name": RESPONSE_SCHEMA_NAME,
        "strict": True,
        "type": "object",
        "required": list(REQUIRED_RESPONSE_FIELDS),
        "additionalProperties": False,
        "properties": {
            "case_id": {"type": "string"},
            "manager_intent": {"type": "string"},
            "workflow_effect": {"type": "string"},
            "target_resolution": {
                "type": "object",
                "description": (
                    "Correction/removal target resolution only. This is for resolving references "
                    "to prior logged meals or items such as a drink, rice, tofu, or an older meal. "
                    "Do not put calorie budget values, daily targets, kcal numbers, or newly logged "
                    "foods in candidate_ids. For daily target updates or ordinary food logs, use "
                    "status='not_applicable' and candidate_ids=[]."
                ),
                "required": ["status", "candidate_ids"],
                "additionalProperties": False,
                "properties": {
                    "status": {
                        "type": "string",
                        "description": (
                            "Use not_applicable when this turn is not resolving a prior meal/item "
                            "target. Use resolved or candidates_available only for correction/removal "
                            "references. Use ambiguous when multiple prior meal/item targets remain."
                        ),
                    },
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "IDs/names of prior meal or item candidates only; never include numeric "
                            "daily calorie targets such as 1800."
                        ),
                    },
                },
            },
            "mutation_request": {
                "type": "object",
                "required": ["requested", "reason"],
                "additionalProperties": False,
                "properties": {
                    "requested": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
            },
            "clarification_question": {"type": ["string", "null"]},
            "confidence_notes": {"type": "string"},
        },
    }


def _provider_input_for_case(case: dict[str, Any]) -> dict[str, Any]:
    expected_context_fields = [str(field) for field in _list_value(case.get("expected_context_fields"))]
    return _json_safe(
        {
            "case_id": _case_id(case),
            "stage": "context_only_single_case_live_probe_preflight",
            "provider_input_mode": "context_contract_preflight_no_provider_call",
            "messages": [
                {
                    "role": "system",
                    "content_contract": {
                        "manager_style": "semantic_decision_from_context_packet",
                        "tools_provide_data_only": True,
                        "deterministic_layer_may_validate_not_select_intent": True,
                    },
                },
                {
                    "role": "user",
                    "content": str(case.get("utterance") or ""),
                },
            ],
            "manager_context_sidecar": {
                "context_policy_version": "manager_context_policy_v1",
                "loaded_context_summary": expected_context_fields,
                "omitted_context_summary": [
                    "raw_trace_dump",
                    "dogfood_review_artifact",
                    "fooddb_gap_candidate_as_truth",
                    "long_term_memory",
                    "debug_artifact",
                ],
                "prior_context": case.get("prior_context"),
                "target_candidates_expected": case.get("target_candidates_expected") is True,
                "pending_pin_expected": case.get("pending_pin_expected") is True,
                "ambiguity_expected": case.get("ambiguity_expected") is True,
            },
            "expected_semantic_contract": {
                "manager_intent": case.get("expected_manager_intent"),
                "workflow_effect": case.get("expected_workflow_effect"),
                "mutation_allowed": False,
                "must_not_happen": _list_value(case.get("must_not_happen")),
                "target_resolution_scope": (
                    "prior_meal_or_item_reference_only_not_daily_budget_or_food_identity"
                ),
            },
            "tool_policy": {
                "tools_available": [],
                "fooddb_used": False,
                "web_tavily_used": False,
                "tool_outputs_as_truth": False,
            },
            "response_schema": _response_schema(),
            "trace_requirements": [
                "provider_input_case_id",
                "context_policy_version",
                "loaded_context_summary",
                "omitted_context_summary",
                "manager_structured_decision",
            ],
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
        }
    )


def _matrix_blockers(matrix: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if matrix.get("artifact_type") != "accurate_intake_context_live_diagnostic_case_matrix":
        blockers.append("matrix.unexpected_artifact_type")
    if matrix.get("status") != "pass":
        blockers.append("matrix.status_not_pass")
    if [str(_object_dict(case).get("case_id") or "") for case in _list_value(matrix.get("cases"))] != list(
        REQUIRED_CASE_IDS
    ):
        blockers.append("matrix.fixed_case_order_mismatch")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(matrix.get(flag)):
            blockers.append(f"matrix.{flag}")
    return blockers


def _anti_overfit_blockers(anti_overfit_guard: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if anti_overfit_guard.get("artifact_type") != "accurate_intake_context_live_diagnostic_anti_overfit_guard":
        blockers.append("anti_overfit_guard.unexpected_artifact_type")
    if anti_overfit_guard.get("status") != "pass":
        blockers.append("anti_overfit_guard.status_not_pass")
    summary = _object_dict(anti_overfit_guard.get("summary"))
    if summary.get("fixed_case_matrix_used") is not True:
        blockers.append("anti_overfit_guard.fixed_case_matrix_not_used")
    if int(summary.get("distinct_intent_count") or 0) < 8:
        blockers.append("anti_overfit_guard.intent_diversity_too_low")
    if int(summary.get("distinct_workflow_effect_count") or 0) < 8:
        blockers.append("anti_overfit_guard.workflow_effect_diversity_too_low")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(anti_overfit_guard.get(flag)):
            blockers.append(f"anti_overfit_guard.{flag}")
    return blockers


def _provider_input_blockers(provider_input: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    case_id = str(provider_input.get("case_id") or "unknown_case")
    if provider_input.get("provider_input_mode") != "context_contract_preflight_no_provider_call":
        blockers.append(f"{case_id}.provider_input_mode_not_preflight")
    schema = _object_dict(provider_input.get("response_schema"))
    if schema.get("name") != RESPONSE_SCHEMA_NAME:
        blockers.append(f"{case_id}.response_schema_name_mismatch")
    if schema.get("strict") is not True:
        blockers.append(f"{case_id}.response_schema_not_strict")
    if tuple(schema.get("required") or ()) != REQUIRED_RESPONSE_FIELDS:
        blockers.append(f"{case_id}.response_schema_required_fields_mismatch")
    context = _object_dict(provider_input.get("manager_context_sidecar"))
    if context.get("context_policy_version") != "manager_context_policy_v1":
        blockers.append(f"{case_id}.context_policy_version_missing")
    loaded = [str(field) for field in _list_value(context.get("loaded_context_summary"))]
    if "context_policy_version" not in loaded:
        blockers.append(f"{case_id}.loaded_context_summary_missing_policy")
    omitted = set(str(field) for field in _list_value(context.get("omitted_context_summary")))
    for forbidden_key in FORBIDDEN_INPUT_KEYS:
        if forbidden_key not in omitted:
            blockers.append(f"{case_id}.forbidden_key_not_omitted:{forbidden_key}")
    tool_policy = _object_dict(provider_input.get("tool_policy"))
    if tool_policy.get("tools_available") != []:
        blockers.append(f"{case_id}.tools_available_not_empty")
    if tool_policy.get("tool_outputs_as_truth") is not False:
        blockers.append(f"{case_id}.tool_outputs_as_truth")
    expected = _object_dict(provider_input.get("expected_semantic_contract"))
    if expected.get("mutation_allowed") is not False:
        blockers.append(f"{case_id}.mutation_allowed")
    if "deterministic_selected_intent" not in _list_value(expected.get("must_not_happen")):
        blockers.append(f"{case_id}.deterministic_intent_guard_missing")
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(provider_input.get(flag)):
            blockers.append(f"{case_id}.{flag}")
    return blockers


def build_context_live_provider_input_preflight_artifact(
    context_live_diagnostic_case_matrix: dict[str, Any] | None = None,
    context_live_diagnostic_anti_overfit_guard: dict[str, Any] | None = None,
    provider_inputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    matrix = _object_dict(
        context_live_diagnostic_case_matrix or build_context_live_diagnostic_case_matrix_artifact()
    )
    anti_overfit_guard = _object_dict(
        context_live_diagnostic_anti_overfit_guard
        or build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    )
    cases = [_object_dict(case) for case in _list_value(matrix.get("cases"))]
    inputs = provider_inputs if provider_inputs is not None else [_provider_input_for_case(case) for case in cases]
    blockers = [
        *_matrix_blockers(matrix),
        *_anti_overfit_blockers(anti_overfit_guard),
    ]
    case_input_rows: list[dict[str, Any]] = []
    for provider_input in inputs:
        row = _object_dict(provider_input)
        input_blockers = _provider_input_blockers(row)
        blockers.extend(input_blockers)
        case_input_rows.append(
            {
                "case_id": row.get("case_id"),
                "provider_input_mode": row.get("provider_input_mode"),
                "response_schema": _object_dict(row.get("response_schema")).get("name"),
                "strict_schema": _object_dict(row.get("response_schema")).get("strict") is True,
                "blockers": input_blockers,
            }
        )
    if [str(row.get("case_id") or "") for row in case_input_rows] != list(REQUIRED_CASE_IDS):
        blockers.append("provider_input_fixed_case_order_mismatch")
    blockers = list(dict.fromkeys(blockers))
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_provider_input_preflight",
            "status": "pass" if not blockers else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_live_provider_input_contract_preflight",
            "diagnostic_only": True,
            "plan_only": True,
            "local_only": True,
            "fixture_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "fixed_case_matrix_used": [str(row.get("case_id") or "") for row in case_input_rows]
            == list(REQUIRED_CASE_IDS),
            "response_schema_name": RESPONSE_SCHEMA_NAME,
            "response_schema_strict": True,
            "required_response_fields": list(REQUIRED_RESPONSE_FIELDS),
            "semantic_owner": "future_live_manager_provider_when_human_approved",
            "deterministic_role": "validate_provider_input_contract_not_select_intent",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "case_count": len(case_input_rows),
                "provider_input_count": len(inputs),
                "blocked_input_count": sum(1 for row in case_input_rows if row["blockers"]),
                "strict_schema_input_count": sum(1 for row in case_input_rows if row["strict_schema"]),
                "target_candidate_inputs": sum(
                    1
                    for provider_input in inputs
                    if _object_dict(provider_input.get("manager_context_sidecar")).get(
                        "target_candidates_expected"
                    )
                    is True
                ),
                "pending_pin_inputs": sum(
                    1
                    for provider_input in inputs
                    if _object_dict(provider_input.get("manager_context_sidecar")).get(
                        "pending_pin_expected"
                    )
                    is True
                ),
            },
            "provider_input_summaries": case_input_rows,
            "provider_inputs": inputs,
            "best_practice_basis": {
                "openai_function_calling": "use schema-defined tool/function interfaces when connecting models to app data or actions",
                "openai_structured_outputs": "strict schema adherence is preferred for structured response contracts",
                "anthropic_tool_use": "tool definitions should provide clear descriptions and input schemas; context should be explicit and bounded",
            },
        }
    )


__all__ = [
    "REQUIRED_RESPONSE_FIELDS",
    "RESPONSE_SCHEMA_NAME",
    "build_context_live_provider_input_preflight_artifact",
]
