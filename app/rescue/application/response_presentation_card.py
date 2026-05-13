from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract

from .response_presentation_contracts import (
    FALSE_OUTPUT_FLAGS,
    PRIMARY_ACTIONS,
    mapping,
)
from .response_presentation_validation import payload_blockers


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.response_presentation_card"
)


def build_rescue_response_card(
    *,
    response_presentation_payload: Mapping[str, Any],
    response_presentation_validation: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *payload_blockers(response_presentation_payload),
        *_validation_blockers(response_presentation_validation),
    ]
    if blockers:
        return _packet(status="blocked", blockers=blockers)
    card_math = mapping(response_presentation_payload.get("card_math"))
    presentation = mapping(response_presentation_validation.get("validated_presentation"))
    proposal_id = str(response_presentation_payload.get("proposal_id") or "")
    return _packet(
        status="pass",
        response_card=_card(
            proposal_id=proposal_id,
            card_math=card_math,
            presentation=presentation,
        ),
        response_text=str(presentation.get("reply_text") or ""),
        proposal_container_ref={
            "proposal_id": proposal_id,
            "proposal_type": "rescue",
            "status": "presented_contract_only",
            "mutation_authority": False,
        },
    )


def _packet(
    *,
    status: str,
    response_card: dict[str, Any] | None = None,
    response_text: str | None = None,
    proposal_container_ref: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_response_card_packet",
        "status": status,
        "owner": "app/rescue",
        "consumer": "future_accept_or_dismiss_rescue_plan_contract",
        "chat_first": True,
        "reply_text": response_text,
        "rescue_response_card": response_card,
        "proposal_container_ref": proposal_container_ref or {},
        "blockers": blockers or [],
        "lab_user_facing_surface_allowed": status == "pass",
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _card(
    *,
    proposal_id: str,
    card_math: Mapping[str, Any],
    presentation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "card_id": proposal_id,
        "proposal_id": proposal_id,
        "overshoot_kcal": card_math.get("overshoot_kcal"),
        "recommended_days": card_math.get("recommended_days"),
        "daily_kcal_adjustment": card_math.get("daily_kcal_adjustment"),
        "cap_mode": str(card_math.get("cap_mode") or ""),
        "effective_from": str(card_math.get("effective_from") or ""),
        "headline": _headline_from_presentation(presentation),
        "summary": _summary_from_presentation(presentation),
        "guardrail_note": "Acceptance is required before any ledger overlay is created.",
        "primary_actions": list(PRIMARY_ACTIONS),
        "negotiation_affordance": mapping(presentation.get("negotiation_affordance")),
        "ui_hints": {
            "display_mode": "single_rescue_proposal_card",
            "backup_options_visible": False,
            "chat_first": True,
            **mapping(presentation.get("ui_hints")),
        },
        "backup_options": [],
    }


def _validation_blockers(validation: Mapping[str, Any]) -> list[str]:
    if validation.get("artifact_type") != "rescue_response_presentation_validation":
        return ["response_presentation_validation.unsupported_artifact_type"]
    if validation.get("status") != "pass":
        return ["response_presentation_validation.status_not_pass"]
    if not mapping(validation.get("validated_presentation")):
        return ["response_presentation_validation.validated_presentation_missing"]
    return []


def _headline_from_presentation(presentation: Mapping[str, Any]) -> str:
    return str(presentation.get("reply_text") or "").split(".")[0].strip()


def _summary_from_presentation(presentation: Mapping[str, Any]) -> str:
    return str(presentation.get("reply_text") or "")


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_response_card",
]
