from __future__ import annotations

import json
from typing import Any

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


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def provider_input_for_case(case: dict[str, Any]) -> dict[str, Any]:
    expected_context_fields = [str(field) for field in list_value(case.get("expected_context_fields"))]
    return json_safe(
        {
            "case_id": str(case.get("case_id") or ""),
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
                {"role": "user", "content": str(case.get("utterance") or "")},
            ],
            "manager_context_sidecar": {
                "context_policy_version": "manager_context_policy_v1",
                "loaded_context_summary": expected_context_fields,
                "omitted_context_summary": list(FORBIDDEN_INPUT_KEYS),
                "prior_context": case.get("prior_context"),
                "target_candidates_expected": case.get("target_candidates_expected") is True,
                "pending_pin_expected": case.get("pending_pin_expected") is True,
                "ambiguity_expected": case.get("ambiguity_expected") is True,
            },
            "expected_semantic_contract": {
                "manager_intent": case.get("expected_manager_intent"),
                "workflow_effect": case.get("expected_workflow_effect"),
                "mutation_allowed": False,
                "must_not_happen": list_value(case.get("must_not_happen")),
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
            "response_schema": response_schema(),
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


def response_schema() -> dict[str, Any]:
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


__all__ = [
    "FORBIDDEN_INPUT_KEYS",
    "FORBIDDEN_TRUTHY_FLAGS",
    "REQUIRED_RESPONSE_FIELDS",
    "RESPONSE_SCHEMA_NAME",
    "claim_is_true",
    "json_safe",
    "list_value",
    "object_dict",
    "provider_input_for_case",
]
