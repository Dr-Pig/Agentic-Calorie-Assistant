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


def manager_context_pack_prompt_payload(
    manager_context_pack: ManagerContextPack | None,
    *,
    primary_packet_present: bool,
) -> dict[str, Any] | None:
    full_payload = manager_context_pack_payload(manager_context_pack)
    if full_payload is None or not primary_packet_present:
        return full_payload
    manager_context = dict(full_payload.get("manager_context") or {})
    available_if_needed = dict(full_payload.get("available_if_needed") or {})
    return {
        "prompt_payload_kind": "manager_context_pack_lineage_summary",
        "primary_context_source": "manager_context_packet_v1",
        "legacy_payload_mode": "packet_primary_reference",
        "policy": {
            "must_inject_count": _list_count(dict(full_payload.get("policy") or {}).get("must_inject")),
            "available_if_needed_field_count": len(available_if_needed),
        },
        "context_packet_carries_full_fields": True,
        "manager_context_field_count": len(manager_context),
        "full_context_omitted_from_prompt": True,
        "read_only": True,
        "mutation_authority": False,
        "deterministic_semantic_authority": False,
    }


def current_turn_context_prompt_payload(
    current_turn_context: CurrentTurnContextV1 | None,
    primary_packet_present: bool = False,
) -> dict[str, Any] | None:
    if current_turn_context is None:
        return None
    payload = current_turn_context.model_dump(mode="json")
    if primary_packet_present:
        return {
            "prompt_payload_kind": "current_turn_context_lineage_summary",
            "primary_context_source": "manager_context_packet_v1",
            "legacy_payload_mode": "packet_primary_reference",
            "context_packet_carries_full_fields": True,
            "full_context_omitted_from_prompt": True,
            "read_only": True,
            "mutation_authority": False,
            "deterministic_semantic_authority": False,
        }
    exposed_keys = (
        "current_interaction_event",
        "active_meal_thread_ref",
        "pending_followup",
        "candidate_attachment_targets",
        "recent_item_targets",
        "target_resolution_posture",
        "context_risk_flags",
        "current_turn_runtime_summary",
    )
    summary = {
        key: payload.get(key)
        for key in exposed_keys
        if payload.get(key) not in (None, [], {})
    }
    summary.update(
        {
            "prompt_payload_kind": "current_turn_context_compact_summary",
            "source_role": "context_engineering_summary",
            "primary_context_source": "manager_context_packet_v1",
            "full_context_omitted_from_prompt": True,
            "read_only": True,
            "mutation_authority": False,
            "omitted_fields": sorted(key for key in payload if key not in exposed_keys),
        }
    )
    return summary


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def manager_context_packet_v1_trace_payload(packet: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(packet, dict):
        return None
    metadata = dict(packet.get("metadata") or {})
    artifact = dict(packet.get("context_loading_artifact") or {})
    recent_chat_window = dict(packet.get("recent_chat_window") or {})
    policy = dict(recent_chat_window.get("policy") or {})
    target_candidates = dict(packet.get("target_candidates") or {})
    return {
        "context_policy_version": metadata.get("context_policy_version"),
        "loaded_context_summary": dict(artifact.get("loaded_context_summary") or {}),
        "omitted_context_summary": dict(artifact.get("omitted_context_summary") or {}),
        "recent_chat_window": {
            "policy": policy,
            "loaded_message_count": artifact.get("loaded_message_count"),
            "omitted_count": artifact.get("omitted_count"),
            "loaded_char_count": artifact.get("loaded_char_count"),
            "char_truncated": artifact.get("char_truncated"),
            "token_budget_status": artifact.get("token_budget_status"),
        },
        "hard_pins_present": {
            "pending_followup": bool(dict(packet.get("hard_pins") or {}).get("pending_followup")),
            "pending_draft": bool(dict(packet.get("hard_pins") or {}).get("pending_draft")),
        },
        "target_candidate_count": len(list(target_candidates.get("for_correction_or_removal") or [])),
        "read_only": True,
        "mutation_authority": False,
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
                "injected_fields": sorted(manager_context_pack.manager_context.keys()),
                "available_if_needed_fields": sorted(manager_context_pack.available_if_needed.keys()),
                "trace_only_fields": sorted(manager_context_pack.trace_only.keys()),
                "promotion_reasons": list(manager_context_pack.promotion_reasons),
            }
        )
    return trace


__all__ = [
    "current_turn_context_prompt_payload",
    "manager_context_pack_payload",
    "manager_context_pack_prompt_payload",
    "manager_context_packet_v1_trace_payload",
    "manager_context_trace_payload",
    "shadow_hypothesis_instruction",
]
