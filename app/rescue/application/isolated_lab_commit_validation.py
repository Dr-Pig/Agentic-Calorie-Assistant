from __future__ import annotations

from typing import Any, Mapping


PRODUCTION_DORMANT_FLAGS = {
    "canonical_mutation_changed": False,
    "production_db_mutation_allowed": False,
    "mainline_activation_enabled": False,
    "mainline_runtime_connected": False,
    "production_scheduler_delivery_allowed": False,
    "durable_product_memory_written_in_mainline": False,
    "manager_context_packet_changed_in_mainline": False,
}


def input_blockers(
    *,
    accept_contract: Mapping[str, Any],
    rescue_response_card_packet: Mapping[str, Any],
    effective_from_policy: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    accepted: Mapping[str, Any],
    card: Mapping[str, Any],
) -> list[str]:
    return [
        *_accept_blockers(accept_contract, accepted),
        *_card_blockers(rescue_response_card_packet, card, accepted),
        *_effective_policy_blockers(effective_from_policy),
        *_budget_blockers(current_budget_view),
    ]


def _accept_blockers(
    accept_contract: Mapping[str, Any],
    accepted: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if accept_contract.get("artifact_type") != "accept_rescue_plan_lab_contract":
        blockers.append("accept_contract.unsupported_artifact_type")
    if accept_contract.get("status") != "pass":
        blockers.append("accept_contract.status_not_pass")
    if not accepted:
        blockers.append("accept_contract.accepted_projection_missing")
    return blockers


def _card_blockers(
    packet: Mapping[str, Any],
    card: Mapping[str, Any],
    accepted: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != "rescue_response_card_packet":
        blockers.append("rescue_response_card_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append("rescue_response_card_packet.status_not_pass")
    if not card:
        blockers.append("rescue_response_card_packet.card_missing")
        return blockers
    if accepted and card.get("proposal_id") != accepted.get("proposal_id"):
        blockers.append("rescue_response_card.proposal_id_mismatch")
    if accepted and card.get("cap_mode") != accepted.get("cap_mode"):
        blockers.append("rescue_response_card.cap_mode_mismatch")
    if to_int(card.get("recommended_days")) <= 0:
        blockers.append("rescue_response_card.recommended_days_invalid")
    if not isinstance(card.get("daily_kcal_adjustment"), int):
        blockers.append("rescue_response_card.daily_kcal_adjustment_missing")
    return blockers


def _effective_policy_blockers(policy: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if policy.get("artifact_type") != "rescue_effective_from_policy":
        blockers.append("effective_from_policy.unsupported_artifact_type")
    if policy.get("status") != "pass":
        blockers.append("effective_from_policy.status_not_pass")
    if not str(policy.get("effective_from_local_date") or ""):
        blockers.append("effective_from_policy.effective_from_local_date_missing")
    if not str(policy.get("effective_start_local_time") or ""):
        blockers.append("effective_from_policy.effective_start_local_time_missing")
    return blockers


def _budget_blockers(view: Mapping[str, Any]) -> list[str]:
    required = (
        "local_date",
        "budget_kcal",
        "consumed_kcal",
        "adjustment_kcal",
        "remaining_kcal",
    )
    return [f"current_budget_view.{field}_missing" for field in required if field not in view]


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def to_int(value: Any) -> int:
    return int(value or 0)


__all__ = ["PRODUCTION_DORMANT_FLAGS", "input_blockers", "mapping", "to_int"]
