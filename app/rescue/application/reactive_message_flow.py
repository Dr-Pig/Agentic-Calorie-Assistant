from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.reactive_message_flow"
)
TRIGGER_ASSESSMENT_ARTIFACT = "rescue_trigger_viability_assessment"
OPTION_GENERATION_ARTIFACT = "rescue_option_generation_result"
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "ledger_entry_created",
    "proposal_committed",
)


def build_reactive_rescue_independent_message_flow(
    *,
    trigger_viability_assessment: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
    source_turn: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(
        trigger_viability_assessment,
        option_generation_result,
    )
    if input_blockers:
        return _flow(
            status="blocked",
            blockers=input_blockers,
            source_turn=source_turn,
        )

    blockers = _flow_blockers(trigger_viability_assessment, option_generation_result)
    if blockers:
        return _flow(status="pass", blockers=blockers, source_turn=source_turn)

    return _flow(
        status="pass",
        rescue_message_created=True,
        independent_message=_independent_message(
            source_turn=source_turn,
            selected_option=_mapping(option_generation_result.get("selected_option")),
        ),
        blockers=[],
        source_turn=source_turn,
    )


def _flow(
    *,
    status: str,
    source_turn: Mapping[str, Any],
    rescue_message_created: bool = False,
    independent_message: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "reactive_rescue_independent_message_flow",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_chat_ux_packet",
        "decision_mode": "deterministic",
        "source_message_event_id": str(source_turn.get("message_event_id") or ""),
        "source_surface": str(source_turn.get("surface") or ""),
        "rescue_message_created": rescue_message_created,
        "message_independent": rescue_message_created,
        "independent_message": independent_message,
        "intake_reply_effects": _intake_reply_effects(source_turn),
        "blockers": blockers or [],
        "proposal_card": None,
        "reply_text": None,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _independent_message(
    *,
    source_turn: Mapping[str, Any],
    selected_option: Mapping[str, Any],
) -> dict[str, Any]:
    source_message_event_id = str(source_turn.get("message_event_id") or "")
    option_key = "|".join(
        [
            source_message_event_id,
            str(selected_option.get("recommended_days") or ""),
            str(selected_option.get("daily_kcal_adjustment") or ""),
        ]
    )
    return {
        "message_id": "rescue-message-" + sha256(option_key.encode("utf-8")).hexdigest()[:12],
        "message_kind": "independent_rescue_message",
        "source_message_event_id": source_message_event_id,
        "rendering_state": "pending_proposal_shaping",
        "contains_formal_proposal": False,
        "selected_option_ref": {
            "rescue_family": str(selected_option.get("rescue_family") or ""),
            "recommended_days": selected_option.get("recommended_days"),
            "daily_kcal_adjustment": selected_option.get("daily_kcal_adjustment"),
        },
    }


def _input_blockers(
    trigger_viability_assessment: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if trigger_viability_assessment.get("artifact_type") != TRIGGER_ASSESSMENT_ARTIFACT:
        blockers.append("trigger_viability_assessment.unsupported_artifact_type")
    if trigger_viability_assessment.get("status") == "blocked":
        blockers.append("trigger_viability_assessment.status_blocked")
    if option_generation_result.get("artifact_type") != OPTION_GENERATION_ARTIFACT:
        blockers.append("option_generation_result.unsupported_artifact_type")
    if option_generation_result.get("status") == "blocked":
        blockers.append("option_generation_result.status_blocked")
    if str(trigger_viability_assessment.get("trigger_type") or "").startswith("proactive"):
        blockers.append("trigger_viability_assessment.not_reactive_trigger")
    for flag in FALSE_INPUT_FLAGS:
        if trigger_viability_assessment.get(flag) is True:
            blockers.append(f"trigger_viability_assessment.{flag}")
        if option_generation_result.get(flag) is True:
            blockers.append(f"option_generation_result.{flag}")
    return blockers


def _flow_blockers(
    trigger_viability_assessment: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
) -> list[str]:
    blockers = [str(item) for item in trigger_viability_assessment.get("blockers") or []]
    blockers.extend(str(item) for item in option_generation_result.get("blockers") or [])
    if trigger_viability_assessment.get("triggered") is not True:
        return list(dict.fromkeys(blockers or ["reactive_trigger_not_triggered"]))
    if option_generation_result.get("selected_option") is None:
        blockers.append("option_generation_result.missing_selected_option")
    return list(dict.fromkeys(blockers))


def _intake_reply_effects(source_turn: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "overshoot_awareness_allowed": bool(source_turn.get("current_intake_reply_id")),
        "formal_rescue_proposal_created": False,
        "ledger_overlay_created": False,
        "rescue_card_attached": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_reactive_rescue_independent_message_flow",
]
