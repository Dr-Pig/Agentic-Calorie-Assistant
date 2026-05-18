from __future__ import annotations

import hashlib
import json
from typing import Any

from app.runtime.agent.manager_prompt_trace_fields import (
    PROVIDER_OVERLAY_OWNER,
    build_manager_prompt_trace_fields,
)
from app.runtime.agent.manager_prompt_runtime_layers import (
    RUNTIME_PAYLOAD_LAYER_KEYS,
    runtime_payload_layer_plan as build_runtime_payload_layer_plan,
)
from app.runtime.agent.manager_system_prompt import single_manager_system_prompt_section_contract

MANAGER_PROMPT_LAYER_CONTRACT_VERSION = "manager_prompt_layer_contract.v1"
MANAGER_PROMPT_CACHE_PROFILE_ID = "manager_prompt_prefix_cache_profile.v1"
MANAGER_SYSTEM_CONTRACT_OWNER = "ManagerRuntime"


def build_manager_prompt_layer_contract(
    *,
    manager_loop_scope: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    system_prompt_id: str = "single_manager_system_prompt",
    system_prompt_version: str = "unknown",
) -> dict[str, Any]:
    dynamic_payload_keys = sorted(str(key) for key in user_payload)
    system_prompt_sha256 = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    dynamic_suffix_sha256 = hashlib.sha256(_json_text(user_payload).encode("utf-8")).hexdigest()
    runtime_payload_layer_plan = build_runtime_payload_layer_plan(dynamic_payload_keys)
    system_section_contract = single_manager_system_prompt_section_contract()
    return {
        "contract_version": MANAGER_PROMPT_LAYER_CONTRACT_VERSION,
        **build_manager_prompt_trace_fields(
            system_prompt_version=str(system_prompt_version),
            system_section_contract=system_section_contract,
            user_payload=user_payload,
            tool_surface_keys=RUNTIME_PAYLOAD_LAYER_KEYS["tool_surface"],
        ),
        "manager_loop_scope": str(manager_loop_scope),
        "system_prompt_layer": "static_prefix",
        "runtime_payload_layer": "dynamic_suffix",
        "provider_profile_layer": "transport_overlay_trace_only",
        "system_prompt_sha256": system_prompt_sha256,
        "dynamic_payload_keys": dynamic_payload_keys,
        "system_contract": {
            "owner": MANAGER_SYSTEM_CONTRACT_OWNER,
            "prompt_id": str(system_prompt_id),
            "prompt_version": str(system_prompt_version),
            "stable_prefix_sha256": system_prompt_sha256,
            **system_section_contract,
        },
        "provider_overlay_contract": {
            "owner": PROVIDER_OVERLAY_OWNER,
            "trace_only": True,
            "may_set_model": True,
            "may_set_transport": True,
            "may_change_system_contract": False,
            "may_change_system_prompt_sections": False,
            "may_inject_product_semantics": False,
        },
        "runtime_payload_layer_plan": runtime_payload_layer_plan,
        "prompt_footprint": _prompt_footprint(
            system_prompt=system_prompt,
            user_payload=user_payload,
            runtime_payload_layer_plan=runtime_payload_layer_plan,
        ),
        "prompt_cache_profile": {
            "profile_id": MANAGER_PROMPT_CACHE_PROFILE_ID,
            "static_prefix_first": True,
            "dynamic_context_last": True,
            "cache_metric_field": "usage.*.cached_tokens",
            "cache_truth_source": "provider_reported_usage_only",
            "stable_prefix_hash_source": "system_contract.stable_prefix_sha256",
            "provider_cache_hit_metric_owner": PROVIDER_OVERLAY_OWNER,
        },
        "prompt_cache_identity": {
            "identity_version": "manager_prompt_cache_identity.v1",
            "stable_prefix_sha256": system_prompt_sha256,
            "dynamic_suffix_sha256": dynamic_suffix_sha256,
            "stable_prefix_component_order": ["system_prompt"],
            "stable_prefix_section_order": list(system_section_contract["section_order"]),
            "dynamic_suffix_component_order": ["runtime_user_payload"],
            "provider_overlay_hash_source": "provider_trace.prompt_cache_request",
            "cache_truth_source": "provider_reported_usage_only",
            "provider_usage_is_cache_truth": True,
        },
        "progressive_disclosure": _progressive_disclosure(user_payload),
}


def _prompt_footprint(
    *,
    system_prompt: str,
    user_payload: dict[str, Any],
    runtime_payload_layer_plan: dict[str, Any],
) -> dict[str, Any]:
    dynamic_sections = [
        _dynamic_section_footprint(section=section, user_payload=user_payload)
        for section in runtime_payload_layer_plan["sections"]
    ]
    largest_dynamic_section = max(
        dynamic_sections,
        key=lambda section: section["utf8_bytes"],
        default={"section_id": None},
    )
    largest_dynamic_key = _largest_dynamic_key(dynamic_sections)
    return {
        "measurement": "json_utf8_bytes_trace_only",
        "provider_usage_is_token_truth": True,
        "token_estimate_used_for_gate": False,
        "system_prompt_chars": len(system_prompt),
        "system_prompt_utf8_bytes": len(system_prompt.encode("utf-8")),
        "dynamic_payload_total_chars": _json_char_count(user_payload),
        "dynamic_payload_total_utf8_bytes": _json_utf8_bytes(user_payload),
        "largest_dynamic_section_id": largest_dynamic_section["section_id"],
        "largest_dynamic_key": largest_dynamic_key,
        "dynamic_sections": dynamic_sections,
    }


def _dynamic_section_footprint(
    *,
    section: dict[str, Any],
    user_payload: dict[str, Any],
) -> dict[str, Any]:
    keys = [str(key) for key in section["keys"]]
    section_payload = {key: user_payload.get(key) for key in keys}
    key_footprints = [
        _dynamic_key_footprint(key=key, value=user_payload.get(key))
        for key in keys
    ]
    largest_key = max(
        key_footprints,
        key=lambda item: item["utf8_bytes"],
        default={"key": None},
    )
    return {
        "section_id": str(section["section_id"]),
        "key_count": len(keys),
        "keys": keys,
        "chars": _json_char_count(section_payload),
        "utf8_bytes": _json_utf8_bytes(section_payload),
        "largest_key": largest_key["key"],
        "key_footprints": key_footprints,
    }


def _dynamic_key_footprint(*, key: str, value: Any) -> dict[str, Any]:
    return {
        "key": key,
        "chars": _json_char_count(value),
        "utf8_bytes": _json_utf8_bytes(value),
    }


def _largest_dynamic_key(dynamic_sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    largest: dict[str, Any] | None = None
    for section in dynamic_sections:
        section_id = str(section.get("section_id") or "")
        for key_footprint in section.get("key_footprints") or []:
            if not isinstance(key_footprint, dict):
                continue
            candidate = {
                "section_id": section_id,
                "key": str(key_footprint.get("key") or ""),
                "utf8_bytes": int(key_footprint.get("utf8_bytes") or 0),
            }
            if largest is None or candidate["utf8_bytes"] > int(largest.get("utf8_bytes") or 0):
                largest = candidate
    return largest


def _progressive_disclosure(user_payload: dict[str, Any]) -> dict[str, Any]:
    context_packet_primary = isinstance(user_payload.get("manager_context_packet_v1"), dict)
    constraints = user_payload.get("constraints")
    dynamic_payload_mode = (
        str(constraints.get("manager_contract_dynamic_payload_mode")) if isinstance(constraints, dict) else None
    )
    compact_contract_constraints = dynamic_payload_mode == "runtime_state_and_refs_only"
    current_turn = user_payload.get("phase_a_current_turn_context")
    context_pack = user_payload.get("phase_a_manager_context_pack")
    legacy_lineage_omitted = context_packet_primary and current_turn is None and context_pack is None
    legacy_lineage_only = (
        context_packet_primary
        and isinstance(current_turn, dict)
        and isinstance(context_pack, dict)
        and current_turn.get("prompt_payload_kind") == "current_turn_context_lineage_summary"
        and context_pack.get("prompt_payload_kind") == "manager_context_pack_lineage_summary"
    )
    legacy_reference_only = (
        legacy_lineage_only
        and current_turn.get("legacy_payload_mode") == "packet_primary_reference"
        and context_pack.get("legacy_payload_mode") == "packet_primary_reference"
    )
    return {
        "full_context_in_user_payload": not (legacy_lineage_only or legacy_lineage_omitted),
        "context_packet_primary": context_packet_primary,
        "primary_context_source": "manager_context_packet_v1" if context_packet_primary else "phase_a_manager_context_pack",
        "legacy_context_payload_mode": _legacy_context_payload_mode(
            legacy_reference_only=legacy_reference_only,
            legacy_lineage_only=legacy_lineage_only,
            legacy_lineage_omitted=legacy_lineage_omitted,
        ),
        "prompt_registry_trace_only": True,
        "provider_metadata_trace_only": True,
        "compact_contract_constraints": compact_contract_constraints,
        "contract_constraints_dynamic_payload_mode": dynamic_payload_mode,
        "contract_static_guidance_refs_only": (
            compact_contract_constraints
            and "manager_contract_policy" not in constraints
            and "manager_contract_policy_summary" not in constraints
            and "manager_contract_evidence_instruction" not in constraints
            and "manager_contract_followup_instruction" not in constraints
            and "manager_contract_examples" not in constraints
        ),
        "tool_results_dynamic_key": "tool_results",
        "manager_context_dynamic_keys": [
            "phase_a_current_turn_context",
            "phase_a_manager_context_pack",
            "manager_context_packet_v1",
        ],
    }


def _legacy_context_payload_mode(
    *,
    legacy_reference_only: bool,
    legacy_lineage_only: bool,
    legacy_lineage_omitted: bool,
) -> str:
    if legacy_lineage_omitted:
        return "packet_primary_omitted_legacy_refs"
    if legacy_reference_only:
        return "packet_primary_reference"
    if legacy_lineage_only:
        return "lineage_summary"
    return "direct_or_compact_summary"


def _json_char_count(value: Any) -> int:
    return len(_json_text(value))


def _json_utf8_bytes(value: Any) -> int:
    return len(_json_text(value).encode("utf-8"))


def _json_text(value: Any) -> str:
    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


__all__ = [
    "MANAGER_PROMPT_CACHE_PROFILE_ID",
    "MANAGER_PROMPT_LAYER_CONTRACT_VERSION",
    "build_manager_prompt_layer_contract",
]
