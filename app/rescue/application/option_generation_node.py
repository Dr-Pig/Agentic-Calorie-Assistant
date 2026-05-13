from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.option_generation_node"
)
TRIGGER_ASSESSMENT_ARTIFACT = "rescue_trigger_viability_assessment"
GUARDRAIL_MATH_ARTIFACT = "rescue_guardrail_math_packet"
ALLOWED_RESCUE_FAMILIES = ["short_horizon_spread"]
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "ledger_entry_created",
    "proposal_committed",
)


def build_rescue_option_generation_result(
    *,
    trigger_viability_assessment: Mapping[str, Any],
    guardrail_math_packet: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(
        trigger_viability_assessment,
        guardrail_math_packet,
    )
    if input_blockers:
        return _result(status="blocked", blockers=input_blockers)

    if trigger_viability_assessment.get("triggered") is not True:
        return _result(
            status="pass",
            recovery_viability="not_assessed",
            blockers=_blockers(trigger_viability_assessment),
        )

    math_blockers = _blockers(guardrail_math_packet)
    recovery_viability = str(guardrail_math_packet.get("recovery_viability") or "")
    if recovery_viability == "non_viable" or math_blockers:
        return _result(
            status="pass",
            recovery_viability=recovery_viability or "non_viable",
            special_posture="rescue_stop_and_escalate",
            blockers=math_blockers,
        )

    option_blockers = _option_field_blockers(guardrail_math_packet)
    if option_blockers:
        return _result(status="blocked", blockers=option_blockers)

    selected = _selected_option(guardrail_math_packet)
    return _result(
        status="pass",
        rescue_needed=True,
        recovery_viability=selected["recovery_viability"],
        special_posture=selected["special_posture"],
        selected_option=selected,
        blockers=[],
    )


def _result(
    *,
    status: str,
    rescue_needed: bool = False,
    recovery_viability: str = "blocked",
    special_posture: str = "blocked",
    selected_option: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    option_count = 1 if selected_option else 0
    return {
        "artifact_type": "rescue_option_generation_result",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_proposal_shaping_node",
        "decision_mode": "deterministic",
        "rescue_needed": rescue_needed,
        "recovery_viability": recovery_viability,
        "allowed_rescue_families": list(ALLOWED_RESCUE_FAMILIES),
        "option_count": option_count,
        "selected_option": selected_option,
        "backup_options": [],
        "candidate_menu": [],
        "recommended_days": None
        if selected_option is None
        else selected_option["recommended_days"],
        "daily_kcal_adjustment": None
        if selected_option is None
        else selected_option["daily_kcal_adjustment"],
        "cap_mode": None if selected_option is None else selected_option["cap_mode"],
        "special_posture": special_posture,
        "guardrail_notes": [
            "single_short_horizon_spread_only",
            "no_multi_family_menu",
            "proposal_required_before_commit",
        ],
        "blockers": blockers or [],
        "proposal_shaping_allowed": status == "pass" and selected_option is not None,
        "proposal_card": None,
        "candidate_copy": None,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _selected_option(guardrail_math_packet: Mapping[str, Any]) -> dict[str, Any]:
    recovery_viability = str(guardrail_math_packet.get("recovery_viability") or "")
    return {
        "rescue_family": "short_horizon_spread",
        "recommended_days": int(guardrail_math_packet["recommended_days"]),
        "daily_kcal_adjustment": int(guardrail_math_packet["daily_kcal_adjustment"]),
        "cap_mode": str(guardrail_math_packet.get("cap_mode") or ""),
        "recovery_viability": recovery_viability,
        "special_posture": _special_posture(recovery_viability),
    }


def _special_posture(recovery_viability: str) -> str:
    if recovery_viability == "strained":
        return "strained_standard_spread"
    return "standard_spread"


def _input_blockers(
    trigger_viability_assessment: Mapping[str, Any],
    guardrail_math_packet: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if trigger_viability_assessment.get("artifact_type") != TRIGGER_ASSESSMENT_ARTIFACT:
        blockers.append("trigger_viability_assessment.unsupported_artifact_type")
    if trigger_viability_assessment.get("status") == "blocked":
        blockers.append("trigger_viability_assessment.status_blocked")
    if guardrail_math_packet.get("artifact_type") != GUARDRAIL_MATH_ARTIFACT:
        blockers.append("guardrail_math_packet.unsupported_artifact_type")
    if guardrail_math_packet.get("status") == "blocked":
        blockers.append("guardrail_math_packet.status_blocked")
    for flag in FALSE_INPUT_FLAGS:
        if trigger_viability_assessment.get(flag) is True:
            blockers.append(f"trigger_viability_assessment.{flag}")
        if guardrail_math_packet.get(flag) is True:
            blockers.append(f"guardrail_math_packet.{flag}")
    return blockers


def _option_field_blockers(guardrail_math_packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not isinstance(guardrail_math_packet.get("recommended_days"), int):
        blockers.append("guardrail_math_packet.missing_recommended_days")
    if not isinstance(guardrail_math_packet.get("daily_kcal_adjustment"), int):
        blockers.append("guardrail_math_packet.missing_daily_kcal_adjustment")
    if not guardrail_math_packet.get("cap_mode"):
        blockers.append("guardrail_math_packet.missing_cap_mode")
    return blockers


def _blockers(packet: Mapping[str, Any]) -> list[str]:
    return [str(item) for item in packet.get("blockers") or []]


__all__ = [
    "ALLOWED_RESCUE_FAMILIES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_option_generation_result",
]
