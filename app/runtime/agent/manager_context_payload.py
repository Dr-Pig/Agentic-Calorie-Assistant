from __future__ import annotations

from typing import Any

from app.runtime.agent.manager_payload_utils import json_safe
from app.runtime.contracts.phase_a import CurrentTurnContextV1, HistoryExpansionPolicy, ManagerContextPack


def shadow_hypothesis_instruction(phase_a_shadow_hypothesis: dict[str, Any] | None) -> dict[str, bool] | None:
    if phase_a_shadow_hypothesis is None:
        return None
    return {
        "not_confirmation": True,
        "must_not_authorize_mutation": True,
        "must_not_upgrade_final_action": True,
        "must_not_upgrade_attachment_or_guard": True,
    }


def _shadow_hypothesis_role(phase_a_shadow_hypothesis: dict[str, Any] | None) -> str:
    if phase_a_shadow_hypothesis is None:
        return "not_supplied"
    return str(phase_a_shadow_hypothesis.get("role") or "tentative_non_authoritative")


def manager_context_pack_payload(manager_context_pack: ManagerContextPack | None) -> dict[str, Any] | None:
    if manager_context_pack is None:
        return None
    return {
        "policy": manager_context_pack.policy.model_dump(mode="json"),
        "manager_context": manager_context_pack.manager_context,
        "available_if_needed": manager_context_pack.available_if_needed,
    }


def manager_context_trace_payload(
    *,
    current_turn_context: CurrentTurnContextV1 | None,
    manager_context_pack: ManagerContextPack | None,
    manager_context_pack_payload: dict[str, Any] | None,
    history_expansion_policy: HistoryExpansionPolicy,
    phase_a_history_expansion_enabled: bool,
    phase_a_shadow_hypothesis: dict[str, Any] | None,
) -> dict[str, Any]:
    phase_a_surface_mode = (
        current_turn_context.current_interaction_event.surface_mode
        if current_turn_context is not None
        else None
    )
    trace: dict[str, Any] = {
        "resolved_state_role": "compatibility_legacy",
        "phase_a_manager_context_pack_role": "missing_structured_context",
        "phase_a_shadow_hypothesis_role": _shadow_hypothesis_role(phase_a_shadow_hypothesis),
        "phase_a_shadow_hypothesis": json_safe(phase_a_shadow_hypothesis),
        "phase_a_shadow_hypothesis_instruction": shadow_hypothesis_instruction(phase_a_shadow_hypothesis),
        "surface_mode": phase_a_surface_mode,
        "history_expansion_policy": history_expansion_policy.model_dump(mode="json"),
        "history_expansion_enabled": phase_a_history_expansion_enabled,
        "context_injection_policy": None,
        "manager_context_pack": None,
        "trace_only_inventory": [],
        "not_for_manager_inventory": [],
    }
    if manager_context_pack is not None:
        trace.update(
            {
                "phase_a_manager_context_pack_role": "primary_structured_context",
                "context_injection_policy": manager_context_pack.policy.model_dump(mode="json"),
                "manager_context_pack": json_safe(manager_context_pack_payload),
                "trace_only_inventory": sorted(manager_context_pack.trace_only.keys()),
                "not_for_manager_inventory": sorted(manager_context_pack.not_for_manager.keys()),
            }
        )
    return trace


__all__ = [
    "manager_context_pack_payload",
    "manager_context_trace_payload",
    "shadow_hypothesis_instruction",
]
