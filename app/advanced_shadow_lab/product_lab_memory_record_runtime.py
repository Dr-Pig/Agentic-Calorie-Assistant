from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_action_projection import (
    memory_action_projection_from_context,
)
from app.advanced_shadow_lab.product_lab_memory_records import DEFAULT_CONSUMERS, scope_keys
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.memory.application.memory_manager_lab_bridge import (
    build_memory_manager_lab_bridge,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_memory_record_runtime"
)


def run_advanced_product_lab_turn_with_memory_records(
    *,
    lab_mode: str,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    shadow_memory_context_pack: Mapping[str, Any],
    enable_lab_memory_record_bridge: bool,
    **runtime_kwargs: Any,
) -> dict[str, Any]:
    bridge = build_product_lab_memory_record_runtime_bridge(
        turn=turn,
        fixture_inputs=fixture_inputs,
        shadow_memory_context_pack=shadow_memory_context_pack,
        enable_lab_memory_record_bridge=enable_lab_memory_record_bridge,
    )
    runtime = run_advanced_product_lab_turn(
        lab_mode=lab_mode,
        turn=turn,
        fixture_inputs=fixture_inputs,
        lab_memory_context_pack=bridge["lab_memory_context_pack"],
        **runtime_kwargs,
    )
    blockers = [
        *list(runtime.get("blockers") or []),
        *[f"memory_record_runtime_bridge.{item}" for item in bridge["blockers"]],
    ]
    status = "blocked" if blockers else str(runtime.get("status") or "blocked")
    return {
        **runtime,
        "status": status,
        "memory_record_runtime_bridge": bridge,
        "memory_record_context_pack_used": bridge["memory_record_context_pack_used"],
        "blockers": blockers,
        "mainline_activation_enabled": False,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
    }


def build_product_lab_memory_record_runtime_bridge(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    shadow_memory_context_pack: Mapping[str, Any],
    enable_lab_memory_record_bridge: bool,
) -> dict[str, Any]:
    manager_bridge = build_memory_manager_lab_bridge(
        manager_input=_manager_input(turn, fixture_inputs),
        shadow_memory_context_pack=shadow_memory_context_pack,
        enable_lab_memory_context=enable_lab_memory_record_bridge,
    )
    attached = manager_bridge["lab_manager_context_attached"] is True
    lab_pack = _lab_context_pack(
        turn=turn,
        context_block=_context_block(manager_bridge) if attached else {},
        blockers=list(manager_bridge.get("blockers") or []),
    )
    return {
        "artifact_type": "advanced_product_lab_memory_record_runtime_bridge",
        "artifact_schema_version": "1.0",
        "status": str(manager_bridge.get("status") or "blocked"),
        "memory_manager_lab_bridge": manager_bridge,
        "lab_memory_context_pack": lab_pack,
        "memory_record_context_pack_used": attached,
        "lab_enabled": enable_lab_memory_record_bridge,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "blockers": list(manager_bridge.get("blockers") or []),
    }


def _lab_context_pack(
    *,
    turn: Mapping[str, Any],
    context_block: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    session_id = str(turn.get("session_id") or "")
    turn_id = str(turn.get("turn_id") or "")
    entries = [_lab_entry(entry) for entry in context_block.get("entries") or []]
    selected_ids = [entry["record_id"] for entry in entries]
    pack = {
        "artifact_type": "advanced_product_lab_memory_context_pack",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "scope_keys": scope_keys(session_id),
        "session_id": session_id,
        "turn_id": turn_id,
        "requested_consumers": list(DEFAULT_CONSUMERS),
        "entries": entries,
        "selected_record_ids": selected_ids,
        "negative_preference_blockers": [
            entry["record_id"]
            for entry in entries
            if entry.get("memory_type") == "negative_preference"
        ],
        "omission_trace": list(context_block.get("omission_trace") or []),
        "token_budget": int(context_block.get("token_estimate") or 0),
        "token_estimate": int(context_block.get("token_estimate") or 0),
        "memory_tools_enabled": True,
        "memory_tool_calls": [
            {"turn_id": turn_id, "tool": "memory.search", "selected_record_ids": selected_ids}
        ],
        "memory_context_injected": bool(entries) and not blockers,
        "lab_manager_context_injected": bool(entries) and not blockers,
        "lab_memory_context_pack_used": bool(entries) and not blockers,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "raw_transcript_included": False,
        "blockers": blockers,
    }
    pack["memory_action_projection"] = memory_action_projection_from_context(pack)
    return pack


def _lab_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    memory_type = _memory_type(str(entry.get("record_type") or ""))
    return {
        "record_id": str(entry.get("record_id") or ""),
        "record_state": "active_lab",
        "memory_type": memory_type,
        "summary": str(entry.get("summary") or ""),
        "source_object_refs": [str(ref) for ref in entry.get("source_refs") or []],
        "review_status": "accepted_lab",
        "intended_consumers": list(DEFAULT_CONSUMERS),
        "freshness_posture": "fresh",
        "store_name": str(entry.get("store_name") or ""),
        "item_names": _items(entry),
        "estimated_kcal": entry.get("estimated_kcal"),
        "blocks_candidate_types": ["recommendation_candidate"]
        if memory_type == "negative_preference"
        else [],
        "blocked_item_patterns": [str(item) for item in entry.get("subject_keys") or []],
        "suppressed_trigger_types": [],
    }


def _items(entry: Mapping[str, Any]) -> list[str]:
    explicit = [str(item) for item in entry.get("item_names") or []]
    return explicit or [str(item) for item in entry.get("subject_keys") or []]


def _manager_input(
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "request_id": str(turn.get("turn_id") or ""),
        "session_id": str(turn.get("session_id") or ""),
        "surface": str(turn.get("surface") or ""),
        "fixture_input_keys": sorted(str(key) for key in fixture_inputs),
    }


def _context_block(manager_bridge: Mapping[str, Any]) -> Mapping[str, Any]:
    augmented = manager_bridge.get("memory_augmented_manager_input")
    if not isinstance(augmented, Mapping):
        return {}
    block = augmented.get("lab_memory_context_block")
    return block if isinstance(block, Mapping) else {}


def _memory_type(record_type: str) -> str:
    return {"confirmed_preference": "preference"}.get(record_type, record_type)


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_product_lab_memory_record_runtime_bridge",
    "run_advanced_product_lab_turn_with_memory_records",
]
