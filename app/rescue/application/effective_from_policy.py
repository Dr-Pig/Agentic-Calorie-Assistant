from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.effective_from_policy"
)
OPTION_GENERATION_ARTIFACT = "rescue_option_generation_result"
SHORT_HORIZON_SPREAD = "short_horizon_spread"
BOUNDARY_LOCAL_TIME = time(hour=11, minute=0)
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "ledger_entry_created",
)


def build_rescue_effective_from_policy(
    *,
    option_generation_result: Mapping[str, Any],
    accepted_at_local: datetime,
    local_date: str,
) -> dict[str, Any]:
    selected_option = _mapping(option_generation_result.get("selected_option"))
    blockers = _input_blockers(option_generation_result, selected_option)
    if blockers:
        return _policy(
            status="blocked",
            blockers=blockers,
            accepted_at_local=accepted_at_local,
        )

    resolved_local_date = date.fromisoformat(local_date)
    posture, effective_date, start_time = _effective_from(
        accepted_at_local=accepted_at_local,
        local_date=resolved_local_date,
    )
    return _policy(
        status="pass",
        blockers=[],
        accepted_at_local=accepted_at_local,
        rescue_family=str(selected_option.get("rescue_family") or ""),
        effective_from_posture=posture,
        effective_from_local_date=effective_date.isoformat(),
        effective_start_local_time=start_time,
    )


def _policy(
    *,
    status: str,
    blockers: list[str],
    accepted_at_local: datetime,
    rescue_family: str | None = None,
    effective_from_posture: str | None = None,
    effective_from_local_date: str | None = None,
    effective_start_local_time: str | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_effective_from_policy",
        "status": status,
        "owner": "app/rescue",
        "consumer": "future_accept_rescue_plan_contract",
        "decision_mode": "deterministic",
        "policy_owner": "L3M_GUARDRAIL_MATH_SPEC.4.7",
        "rescue_family": rescue_family,
        "accepted_at_local": accepted_at_local.isoformat(),
        "boundary_local_time": "11:00",
        "effective_from_posture": effective_from_posture,
        "effective_from_local_date": effective_from_local_date,
        "effective_start_local_time": effective_start_local_time,
        "blockers": blockers,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _input_blockers(
    option_generation_result: Mapping[str, Any],
    selected_option: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if option_generation_result.get("artifact_type") != OPTION_GENERATION_ARTIFACT:
        blockers.append("option_generation_result.unsupported_artifact_type")
    if option_generation_result.get("status") == "blocked":
        blockers.append("option_generation_result.status_blocked")
    if not selected_option:
        blockers.append("option_generation_result.missing_selected_option")
    elif selected_option.get("rescue_family") != SHORT_HORIZON_SPREAD:
        blockers.append(
            f"unsupported_rescue_family:{selected_option.get('rescue_family')}"
        )
    for flag in FALSE_INPUT_FLAGS:
        if option_generation_result.get(flag) is True:
            blockers.append(f"option_generation_result.{flag}")
    return blockers


def _effective_from(
    *,
    accepted_at_local: datetime,
    local_date: date,
) -> tuple[str, date, str]:
    if accepted_at_local.time() < BOUNDARY_LOCAL_TIME:
        return "today", local_date, "after_lunch"
    return "tomorrow", local_date + timedelta(days=1), "00:00"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "BOUNDARY_LOCAL_TIME",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_effective_from_policy",
]
