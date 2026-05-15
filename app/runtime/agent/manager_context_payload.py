from __future__ import annotations

from typing import Any

from app.runtime.agent.manager_context_post_tool_projection import (
    compact_active_day_state_after_tool_evidence,
    compact_hard_pins_after_tool_evidence,
)
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
    if primary_packet_present:
        return None
    full_payload = manager_context_pack_payload(manager_context_pack)
    return full_payload


def current_turn_context_prompt_payload(
    current_turn_context: CurrentTurnContextV1 | None,
    primary_packet_present: bool = False,
) -> dict[str, Any] | None:
    if current_turn_context is None:
        return None
    if primary_packet_present:
        return None
    payload = current_turn_context.model_dump(mode="json")
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


def manager_context_packet_v1_prompt_payload(
    packet: dict[str, Any] | None,
    *,
    tool_results: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(packet, dict):
        return None
    metadata = dict(packet.get("metadata") or {})
    artifact = dict(packet.get("context_loading_artifact") or {})
    recent_chat_window = dict(packet.get("recent_chat_window") or {})
    if _post_tool_context_reference_allowed(tool_results):
        target_candidates = dict(packet.get("target_candidates") or {})
        return {
            "prompt_payload_kind": "manager_context_packet_v1_post_tool_reference",
            "metadata": {
                "local_date": metadata.get("local_date"),
                "context_policy_version": metadata.get("context_policy_version"),
                "claim_scope": metadata.get("claim_scope"),
            },
            "current_turn": _compact_current_turn(dict(packet.get("current_turn") or {})),
            "recent_chat_window": {
                "loaded_message_count": artifact.get("loaded_message_count"),
                "omitted_count": artifact.get("omitted_count"),
                "char_truncated": artifact.get("char_truncated"),
                "token_budget_status": artifact.get("token_budget_status"),
                "messages_omitted_after_tool_evidence": True,
            },
            "hard_pins": compact_hard_pins_after_tool_evidence(packet.get("hard_pins")),
            "active_day_state": compact_active_day_state_after_tool_evidence(
                packet.get("active_day_state")
            ),
            "target_candidates": {
                "candidate_count": len(list(target_candidates.get("for_correction_or_removal") or [])),
                "candidates_omitted_after_tool_evidence": True,
                "read_only": True,
                "mutation_authority": False,
            },
            "constraints": list(packet.get("constraints") or []),
            "read_only": True,
            "mutation_authority": False,
        }
    return {
        "prompt_payload_kind": "manager_context_packet_v1_prompt_compact",
        "metadata": {
            "local_date": metadata.get("local_date"),
            "context_policy_version": metadata.get("context_policy_version"),
            "claim_scope": metadata.get("claim_scope"),
        },
        "current_turn": _compact_current_turn(dict(packet.get("current_turn") or {})),
        "recent_chat_window": {
            "messages": list(recent_chat_window.get("messages") or []),
            "loaded_message_count": artifact.get("loaded_message_count"),
            "omitted_count": artifact.get("omitted_count"),
            "char_truncated": artifact.get("char_truncated"),
            "token_budget_status": artifact.get("token_budget_status"),
        },
        "hard_pins": dict(packet.get("hard_pins") or {}),
        "active_day_state": dict(packet.get("active_day_state") or {}),
        "target_candidates": dict(packet.get("target_candidates") or {}),
        "constraints": list(packet.get("constraints") or []),
        "read_only": True,
        "mutation_authority": False,
    }


def _post_tool_context_reference_allowed(tool_results: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None) -> bool:
    evidence_tools = {"estimate_nutrition", "user_provided_kcal_evidence", "resolve_correction_target", "compare_against_budget"}
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or item.get("name") or "").strip()
        if tool_name in evidence_tools:
            return True
    return False


def _compact_current_turn(current_turn: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel": current_turn.get("channel"),
        "manager_mode": current_turn.get("manager_mode"),
        "interaction_event": _compact_interaction_event_prompt_payload(
            current_turn.get("interaction_event")
        ),
        "read_only": True,
        "mutation_authority": False,
    }


def _compact_interaction_event_prompt_payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    payload = dict(value)
    payload.pop("raw_text", None)
    return payload


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
    "manager_context_packet_v1_prompt_payload",
    "manager_context_packet_v1_trace_payload",
    "manager_context_trace_payload",
    "shadow_hypothesis_instruction",
]
