from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .proposal_shaping_contracts import (
    COPY_FIELDS,
    DETERMINISTIC_FIELDS,
    FALSE_OUTPUT_FLAGS,
    FORBIDDEN_AUTHORITY_FIELDS,
    mapping,
)


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_validation"
)
MUTATION_TOKENS = ("saved", "committed", "applied", "updated your budget")
DELIVERY_TOKENS = ("sent", "delivered", "notify", "notification", "push")


def validate_rescue_proposal_shaping_output(
    *,
    proposal_shaping_payload: Mapping[str, Any],
    candidate_output: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = payload_blockers(proposal_shaping_payload)
    option = mapping(proposal_shaping_payload.get("deterministic_option"))
    candidate_blockers = [] if input_blockers else _candidate_blockers(candidate_output, option)
    blockers = [*input_blockers, *candidate_blockers]
    status = "blocked" if input_blockers else "fail" if candidate_blockers else "pass"
    return {
        "artifact_type": "rescue_proposal_shaping_output_validation",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_response_presentation",
        "copy_guard_passed": status == "pass",
        "deterministic_option": dict(option),
        "shaped_proposal": None
        if status != "pass"
        else _shaped_proposal(candidate_output),
        "blockers": blockers,
        "lab_user_facing_surface_allowed": status == "pass",
        **dict(FALSE_OUTPUT_FLAGS),
    }


def payload_blockers(payload: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") != "rescue_proposal_shaping_payload":
        blockers.append("proposal_shaping_payload.unsupported_artifact_type")
    if payload.get("status") != "pass":
        blockers.append("proposal_shaping_payload.status_not_pass")
    for flag in FALSE_OUTPUT_FLAGS:
        if payload.get(flag) is True:
            blockers.append(f"proposal_shaping_payload.{flag}")
    return blockers


def blocked_validation(payload: Mapping[str, Any], blockers: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_proposal_shaping_output_validation",
        "status": "blocked",
        "deterministic_option": dict(mapping(payload.get("deterministic_option"))),
        "shaped_proposal": None,
        "copy_guard_passed": False,
        "blockers": blockers,
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _candidate_blockers(output: Mapping[str, Any], option: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in COPY_FIELDS:
        if not str(output.get(field) or "").strip():
            blockers.append(f"candidate_output.{field}_missing")
    if output.get("claim_scope") != "lab_proposal_shaping_only":
        blockers.append("candidate_output.claim_scope_not_lab_proposal_shaping")
    for field in DETERMINISTIC_FIELDS:
        if field in output and output.get(field) != option.get(field):
            blockers.append(f"candidate_output.{field}_override")
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        if _has_value(output.get(field)):
            blockers.append(f"candidate_output.{field}_forbidden")
    for key in ("action_request", "delivery_request", "mutation_request"):
        if output.get(key) is True:
            blockers.append(f"candidate_output.{key}_not_allowed")
    text = _joined_copy_text(output)
    if any(token in text for token in DELIVERY_TOKENS):
        blockers.append("candidate_output.delivery_language_present")
    if any(token in text for token in MUTATION_TOKENS):
        blockers.append("candidate_output.mutation_language_present")
    return blockers


def _shaped_proposal(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_headline": str(output.get("proposal_headline") or ""),
        "proposal_summary": str(output.get("proposal_summary") or ""),
        "coaching_frame": str(output.get("coaching_frame") or ""),
        "quick_action_posture": str(output.get("quick_action_posture") or ""),
        "reason_codes": [str(item) for item in output.get("reason_codes") or []],
    }


def _joined_copy_text(output: Mapping[str, Any]) -> str:
    return " ".join(str(output.get(field) or "") for field in COPY_FIELDS).lower()


def _has_value(value: Any) -> bool:
    return value not in (None, False, [], {})


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "blocked_validation",
    "payload_blockers",
    "validate_rescue_proposal_shaping_output",
]
