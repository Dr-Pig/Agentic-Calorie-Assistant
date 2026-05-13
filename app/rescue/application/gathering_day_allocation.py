from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.planned_event_budget_allocation import (
    build_planned_event_budget_allocation,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.gathering_day_allocation"
)
INFORMATIONAL_REQUEST = "informational"
RESERVE_REQUESTS = {"reserve_budget", "set_budget"}


def build_gathering_day_allocation_result(
    *,
    gathering_context: Mapping[str, Any],
    read_model_input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    request_type = str(gathering_context.get("request_type") or "")
    if request_type == INFORMATIONAL_REQUEST:
        return _result(
            status="pass",
            mode="informational_allocation",
            guidance_packet=_guidance_packet(gathering_context),
            confirmation_required=False,
        )
    if request_type in RESERVE_REQUESTS:
        allocation = build_planned_event_budget_allocation(
            planned_event_context=_planned_event_context(gathering_context),
            read_model_input_packet=read_model_input_packet,
        )
        return _result(
            status=str(allocation.get("status") or "blocked"),
            mode="reserve_budget_proposal_seed",
            proposal_seed_created=allocation.get("status") == "pass",
            confirmation_required=True,
            planned_event_allocation=allocation,
            blockers=[str(item) for item in allocation.get("blockers") or []],
        )
    return _result(
        status="blocked",
        mode="needs_clarification",
        blockers=[f"gathering_context.request_type_unsupported:{request_type}"],
    )


def _result(
    *,
    status: str,
    mode: str,
    guidance_packet: dict[str, Any] | None = None,
    planned_event_allocation: Mapping[str, Any] | None = None,
    proposal_seed_created: bool = False,
    confirmation_required: bool = False,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "gathering_day_allocation_result",
        "status": status,
        "owner": "app/rescue",
        "consumer": "gathering_day_chat_flow",
        "decision_mode": "deterministic",
        "mode": mode,
        "guidance_packet": guidance_packet,
        "planned_event_allocation": dict(planned_event_allocation or {}),
        "proposal_seed_created": proposal_seed_created,
        "confirmation_required": confirmation_required,
        "proposal_commit_allowed": False,
        "blockers": blockers or [],
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _guidance_packet(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "primary_surface": "chat",
        "event_id": str(context.get("event_id") or ""),
        "event_label": str(context.get("event_label") or ""),
        "event_local_date": str(context.get("event_local_date") or ""),
        "guidance_kind": "informational_gathering_day_allocation",
        "proposal_affordance": "ask_to_reserve_or_set_budget",
        "does_not_mutate_budget": True,
    }


def _planned_event_context(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(context.get("event_id") or ""),
        "event_label": str(context.get("event_label") or ""),
        "event_local_date": str(context.get("event_local_date") or ""),
        "reserve_kcal": _int(context.get("reserve_kcal")),
        "planning_days_before_event": _int(context.get("planning_days_before_event")),
        "source_refs": [
            str(ref)
            for ref in context.get("source_refs") or []
            if str(ref).startswith("planned_event:")
        ],
    }


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_gathering_day_allocation_result",
]
