from __future__ import annotations

from typing import Any


FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID = "founder_live_contract"
FOUNDER_LIVE_MANAGER_SCHEMA_NAME = "founder_live_manager_contract"
FOUNDER_LIVE_MANAGER_SCHEMA_VERSION = "v1"
FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY = "synthetic_tool_transport"
FOUNDER_LIVE_MANAGER_TOOL_NAME = "manager_structured_decision"

FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS = [
    "manager_action",
    "intent",
    "intent_type",
    "workflow_effect",
    "target_attachment",
    "exactness",
    "confidence",
    "evidence_posture",
    "semantic_decision",
    "answer_contract",
]

FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS = {
    "manager_action": "manager_loop_control",
    "intent": "runtime_router_and_trace_classifier",
    "intent_type": "active_runtime_router",
    "workflow_effect": "transition_guard_and_mutation_boundary",
    "target_attachment": "meal_thread_attachment_and_correction_path",
    "exactness": "nutrition_final_mapping_and_renderer_exactness_guard",
    "confidence": "uncertainty_and_evidence_honesty_trace",
    "evidence_posture": "b2_evidence_and_final_mapping_guard",
    "semantic_decision": "semantic_owner_trace_and_final_mapping_alignment",
    "answer_contract": "renderer_boundary",
}

FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES = [
    "complete_onboarding",
    "answer_remaining_budget",
    "onboarding_required",
    "manager_unavailable",
    "log_meal",
]


FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT = {
    "complete_onboarding": "complete_onboarding",
    "answer_remaining_budget": "answer_remaining_budget",
    "log_meal": "log_meal",
    "correct_meal": "log_meal",
}


def is_founder_live_manager_contract(constraints: dict[str, Any] | None) -> bool:
    if not isinstance(constraints, dict):
        return False
    return str(constraints.get("manager_contract_profile_id") or "") == FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID


def founder_live_manager_contract_constraints(profile_id: str) -> dict[str, Any]:
    return {
        "manager_contract_profile_id": FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID,
        "manager_contract_provider_profile_id": profile_id,
        "manager_contract_schema_name": FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
        "manager_contract_schema_version": FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
        "manager_contract_transport_policy": FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
    }


def validate_founder_live_manager_contract_consistency(payload: dict[str, Any]) -> None:
    semantic_decision = payload.get("semantic_decision")
    if not isinstance(semantic_decision, dict):
        return
    semantic_intent = str(semantic_decision.get("current_turn_intent") or "")
    expected_intent_type = FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT.get(semantic_intent)
    if expected_intent_type is None:
        return
    observed_intent_type = str(payload.get("intent_type") or "")
    if observed_intent_type != expected_intent_type:
        raise RuntimeError(
            "founder live manager contract intent_type mismatch: "
            f"semantic_decision.current_turn_intent={semantic_intent!r} "
            f"requires intent_type={expected_intent_type!r}, observed {observed_intent_type!r}"
        )


__all__ = [
    "FOUNDER_LIVE_MANAGER_CONTRACT_PROFILE_ID",
    "FOUNDER_LIVE_MANAGER_FIELD_CONSUMERS",
    "FOUNDER_LIVE_MANAGER_ALLOWED_INTENT_TYPES",
    "FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT",
    "FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS",
    "FOUNDER_LIVE_MANAGER_SCHEMA_NAME",
    "FOUNDER_LIVE_MANAGER_SCHEMA_VERSION",
    "FOUNDER_LIVE_MANAGER_TOOL_NAME",
    "FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY",
    "founder_live_manager_contract_constraints",
    "is_founder_live_manager_contract",
    "validate_founder_live_manager_contract_consistency",
]
