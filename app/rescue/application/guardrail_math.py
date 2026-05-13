from __future__ import annotations

from math import ceil
from typing import Any, Mapping

from app.rescue.domain.guardrail_math_rules import (
    RecoveryViability,
    daily_cap,
    math_blockers,
    overshoot,
    overshoot_summary,
    recommended_days,
    recovery_viability,
    safety_floor,
    target_day_checks,
    target_days,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.guardrail_math"
)
READ_MODEL_PACKET_ARTIFACT = "rescue_read_model_input_packet"
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "mainline_activation_enabled",
    "mainline_runtime_connected",
)


def build_rescue_guardrail_math_packet(
    *,
    read_model_input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(read_model_input_packet)
    if input_blockers:
        return _packet(
            status="blocked",
            recovery_viability="blocked",
            blockers=input_blockers,
        )

    current_budget = _mapping(read_model_input_packet.get("current_budget_view"))
    body_plan = _mapping(read_model_input_packet.get("active_body_plan_view"))
    overshoot_kcal = overshoot(current_budget)
    targets = target_days(body_plan)
    cap_kcal = daily_cap(targets)
    days = recommended_days(
        overshoot_kcal=overshoot_kcal,
        daily_cap_kcal=cap_kcal,
        target_day_count=len(targets),
    )
    daily_recovery = ceil(overshoot_kcal / days) if days and overshoot_kcal > 0 else 0
    checks = target_day_checks(
        target_days=targets[: days or len(targets)],
        daily_recovery_kcal=daily_recovery,
        safety_floor_kcal=safety_floor(body_plan),
    )
    blockers = math_blockers(
        overshoot_kcal=overshoot_kcal,
        daily_cap_kcal=cap_kcal,
        recommended_days_value=days,
        target_day_count=len(targets),
        checks=checks,
    )
    return _packet(
        status="pass",
        recovery_viability=recovery_viability(blockers, checks),
        blockers=blockers,
        overshoot_summary=overshoot_summary(current_budget, overshoot_kcal),
        recommended_days=None if blockers else days,
        daily_kcal_adjustment=None if blockers else -daily_recovery,
        target_day_checks=checks,
    )


def _packet(
    *,
    status: str,
    recovery_viability: RecoveryViability,
    blockers: list[str],
    overshoot_summary: Mapping[str, int] | None = None,
    recommended_days: int | None = None,
    daily_kcal_adjustment: int | None = None,
    target_day_checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_guardrail_math_packet",
        "status": status,
        "owner": "app/rescue",
        "consumer": "trigger_and_viability_assessment_node",
        "decision_mode": "deterministic",
        "llm_math_truth_allowed": False,
        "overshoot_summary": dict(overshoot_summary or {}),
        "recovery_viability": recovery_viability,
        "recommended_days": recommended_days,
        "daily_kcal_adjustment": daily_kcal_adjustment,
        "cap_mode": "standard_15_percent",
        "target_day_checks": target_day_checks or [],
        "blockers": blockers,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _input_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != READ_MODEL_PACKET_ARTIFACT:
        blockers.append("read_model_input_packet.unsupported_artifact_type")
    if packet.get("status") == "blocked":
        blockers.append("read_model_input_packet.status_blocked")
    for flag in FALSE_INPUT_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"read_model_input_packet.{flag}")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_guardrail_math_packet",
]
