from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .response_presentation_contracts import (
    FALSE_OUTPUT_FLAGS,
    PRIMARY_ACTIONS,
    SECONDARY_INTENTS,
    mapping,
)


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.response_presentation_validation"
)
MATH_FIELDS = ("recommended_days", "daily_kcal_adjustment", "cap_mode", "effective_from")
MUTATION_TOKENS = ("saved", "committed", "applied", "updated your budget")
DELIVERY_TOKENS = ("sent", "delivered", "notify", "notification", "push")


def validate_rescue_response_presentation_output(
    *,
    response_presentation_payload: Mapping[str, Any],
    candidate_output: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = payload_blockers(response_presentation_payload)
    card_math = mapping(response_presentation_payload.get("card_math"))
    candidate_blockers = [] if input_blockers else _candidate_blockers(candidate_output, card_math)
    blockers = [*input_blockers, *candidate_blockers]
    status = "blocked" if input_blockers else "fail" if candidate_blockers else "pass"
    return {
        "artifact_type": "rescue_response_presentation_validation",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_response_card",
        "primary_actions_guard_passed": status == "pass",
        "card_math": dict(card_math),
        "validated_presentation": None
        if status != "pass"
        else _validated_presentation(candidate_output),
        "blockers": blockers,
        "lab_user_facing_surface_allowed": status == "pass",
        **dict(FALSE_OUTPUT_FLAGS),
    }


def payload_blockers(payload: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") != "rescue_response_presentation_payload":
        blockers.append("response_presentation_payload.unsupported_artifact_type")
    if payload.get("status") != "pass":
        blockers.append("response_presentation_payload.status_not_pass")
    if payload.get("primary_actions_contract") != PRIMARY_ACTIONS:
        blockers.append("response_presentation_payload.primary_actions_contract_invalid")
    for flag in FALSE_OUTPUT_FLAGS:
        if payload.get(flag) is True:
            blockers.append(f"response_presentation_payload.{flag}")
    return blockers


def blocked_validation(payload: Mapping[str, Any], blockers: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_response_presentation_validation",
        "status": "blocked",
        "card_math": dict(mapping(payload.get("card_math"))),
        "validated_presentation": None,
        "primary_actions_guard_passed": False,
        "blockers": blockers,
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _candidate_blockers(output: Mapping[str, Any], card_math: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not str(output.get("reply_text") or "").strip():
        blockers.append("candidate_output.reply_text_missing")
    actions = list(output.get("primary_actions") or [])
    if actions != PRIMARY_ACTIONS:
        blockers.append("candidate_output.primary_actions_must_match_contract")
    blockers.extend(_action_shape_blockers(actions))
    blockers.extend(_negotiation_blockers(candidate=output))
    if output.get("claim_scope") != "lab_response_presentation_only":
        blockers.append("candidate_output.claim_scope_not_lab_response_presentation")
    for field in MATH_FIELDS:
        if field in output and output.get(field) != card_math.get(field):
            blockers.append(f"candidate_output.{field}_override")
    for key in ("action_request", "delivery_request", "mutation_request"):
        if output.get(key) is True:
            blockers.append(f"candidate_output.{key}_not_allowed")
    text = str(output.get("reply_text") or "").lower()
    if any(token in text for token in DELIVERY_TOKENS):
        blockers.append("candidate_output.delivery_language_present")
    if any(token in text for token in MUTATION_TOKENS):
        blockers.append("candidate_output.mutation_language_present")
    return blockers


def _action_shape_blockers(actions: list[Any]) -> list[str]:
    blockers: list[str] = []
    for action in actions:
        item = mapping(action)
        action_id = str(item.get("action_id") or "")
        if not str(item.get("label") or ""):
            blockers.append(f"candidate_output.primary_action_label_missing:{action_id}")
    return blockers


def _negotiation_blockers(*, candidate: Mapping[str, Any]) -> list[str]:
    affordance = mapping(candidate.get("negotiation_affordance"))
    blockers: list[str] = []
    if affordance.get("not_primary_actions") is not True:
        blockers.append("candidate_output.negotiation_affordance.not_primary_actions_not_true")
    if affordance.get("allowed_secondary_intents") != SECONDARY_INTENTS:
        blockers.append("candidate_output.negotiation_affordance.secondary_intents_mismatch")
    return blockers


def _validated_presentation(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "reply_text": str(output.get("reply_text") or ""),
        "primary_actions": list(PRIMARY_ACTIONS),
        "negotiation_affordance": mapping(output.get("negotiation_affordance")),
        "ui_hints": mapping(output.get("ui_hints")),
        "reason_codes": [str(item) for item in output.get("reason_codes") or []],
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "blocked_validation",
    "payload_blockers",
    "validate_rescue_response_presentation_output",
]
