from __future__ import annotations

from math import ceil
from typing import Any, Literal, Mapping

from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.option_generation_shadow"
)
RecoveryViability = Literal["viable", "strained", "non_viable", "blocked"]
VIABILITY_ARTIFACT = "rescue_no_commit_viability_shadow_packet"
FALSE_INPUT_FLAGS = (
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
    "ledger_entry_created",
)
BASE_GUARDRAIL_NOTES = [
    "daily_cap_denominator_is_base_budget",
    "safety_floor_checked",
    "proposal_required_before_commit",
]


def build_rescue_option_generation_shadow_packet(
    *,
    viability_shadow_packet: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(viability_shadow_packet)
    option = _option_values(viability_shadow_packet) if not input_blockers else _blocked_option()
    blockers = [*input_blockers, *option["blockers"]]
    return {
        "artifact_type": "rescue_option_generation_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if input_blockers else "pass",
        "owner": "app/rescue",
        "consumer": "future_rescue_proposal_shaping_shadow_review",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "viability_shadow_packet_used": not input_blockers,
        "rescue_needed": option["rescue_needed"],
        "recovery_viability": option["recovery_viability"],
        "recommended_days": option["recommended_days"],
        "daily_kcal_adjustment": option["daily_kcal_adjustment"],
        "cap_mode": "standard_15_percent",
        "special_posture": option["special_posture"],
        "guardrail_notes": option["guardrail_notes"],
        "blockers": blockers,
        "proposal_card": None,
        "proposal_headline": None,
        "proposal_summary": None,
        "coaching_frame": None,
        "quick_action_posture": None,
        "candidate_copy": None,
        "send_or_skip": None,
        "primary_actions": [],
        "runtime_effect_allowed": False,
        "recommendation_posture_updated": False,
        "ledger_entry_created": False,
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def _input_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != VIABILITY_ARTIFACT:
        blockers.append("viability_shadow_packet.unsupported_artifact_type")
    if packet.get("status") == "blocked":
        blockers.append("viability_shadow_packet.status_blocked")
    for flag in FALSE_INPUT_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"viability_shadow_packet.{flag}")
    if not _target_checks(packet):
        blockers.append("viability_shadow_packet.missing_target_day_checks")
    return blockers


def _option_values(packet: Mapping[str, Any]) -> dict[str, Any]:
    overshoot = _overshoot(packet)
    daily_cap = _daily_cap(packet)
    if overshoot <= 0:
        return _non_viable("logging_first_rescue", ["no_overshoot"])
    if daily_cap <= 0:
        return _non_viable("rescue_stop_and_escalate", ["missing_daily_cap"])

    min_days = ceil(overshoot / daily_cap)
    if min_days > 5:
        return _non_viable(
            "rescue_stop_and_escalate",
            ["min_days_exceeds_5"],
            ["escalate_to_calibration_review"],
        )

    daily_recovery = ceil(overshoot / min_days)
    viability = _viability_for_daily_recovery(packet, daily_recovery)
    notes = list(BASE_GUARDRAIL_NOTES)
    if viability == "strained":
        notes.append("daily_adjustment_above_10_percent")
    return {
        "rescue_needed": True,
        "recovery_viability": viability,
        "recommended_days": min_days,
        "daily_kcal_adjustment": -daily_recovery,
        "special_posture": "standard_spread",
        "guardrail_notes": notes,
        "blockers": [],
    }


def _non_viable(
    special_posture: str,
    blockers: list[str],
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "rescue_needed": False,
        "recovery_viability": "non_viable",
        "recommended_days": None,
        "daily_kcal_adjustment": None,
        "special_posture": special_posture,
        "guardrail_notes": [*BASE_GUARDRAIL_NOTES, *(notes or [])],
        "blockers": blockers,
    }


def _blocked_option() -> dict[str, Any]:
    return {
        "rescue_needed": False,
        "recovery_viability": "blocked",
        "recommended_days": None,
        "daily_kcal_adjustment": None,
        "special_posture": "blocked",
        "guardrail_notes": [],
        "blockers": [],
    }


def _viability_for_daily_recovery(
    packet: Mapping[str, Any],
    daily_recovery: int,
) -> RecoveryViability:
    strained = False
    for check in _target_checks(packet):
        if daily_recovery > _int(check.get("max_15_percent_kcal")):
            return "non_viable"
        if daily_recovery > _int(check.get("max_10_percent_kcal")):
            strained = True
        if _candidate_effective_budget(check, daily_recovery) < _int(check.get("safety_floor_kcal")):
            return "non_viable"
    return "strained" if strained else "viable"


def _candidate_effective_budget(check: Mapping[str, Any], daily_recovery: int) -> int:
    original_overlay = abs(_int(check.get("proposed_rescue_overlay_kcal")))
    original_candidate = _int(check.get("candidate_effective_budget_kcal"))
    return original_candidate + original_overlay - daily_recovery


def _daily_cap(packet: Mapping[str, Any]) -> int:
    caps = [_int(check.get("max_15_percent_kcal")) for check in _target_checks(packet)]
    return min(caps) if caps else 0


def _overshoot(packet: Mapping[str, Any]) -> int:
    summary = packet.get("overshoot_summary")
    if not isinstance(summary, Mapping):
        return 0
    return _int(summary.get("overshoot_kcal"))


def _target_checks(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    checks = packet.get("target_day_checks")
    if not isinstance(checks, list):
        return []
    return [item for item in checks if isinstance(item, Mapping)]


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_option_generation_shadow_packet",
]
