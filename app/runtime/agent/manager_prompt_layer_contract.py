from __future__ import annotations

import hashlib
import json
from typing import Any


MANAGER_PROMPT_LAYER_CONTRACT_VERSION = "manager_prompt_layer_contract.v1"
MANAGER_PROMPT_CACHE_PROFILE_ID = "manager_prompt_prefix_cache_profile.v1"
MANAGER_SYSTEM_CONTRACT_OWNER = "ManagerRuntime"
PROVIDER_OVERLAY_OWNER = "ProviderAdapter"
_RUNTIME_PAYLOAD_LAYER_ORDER = (
    "turn_state",
    "context_engineering",
    "tool_surface",
    "tool_evidence",
    "contract_constraints",
    "loop_control",
    "guard_repair",
)
_RUNTIME_PAYLOAD_LAYER_KEYS = {
    "turn_state": (
        "raw_user_input",
        "resolved_state",
        "resolved_state_role",
        "onboarding_payload",
    ),
    "context_engineering": (
        "phase_a_current_turn_context",
        "phase_a_manager_context_pack",
        "manager_context_packet_v1",
        "phase_a_manager_context_pack_role",
        "phase_a_surface_mode",
        "phase_a_context_pack_version",
        "phase_a_history_expansion_policy",
        "phase_a_history_expansion_enabled",
        "phase_a_shadow_hypothesis",
        "phase_a_shadow_hypothesis_role",
        "phase_a_shadow_hypothesis_instruction",
    ),
    "tool_surface": (
        "available_tools",
        "manager_scope_policy",
    ),
    "tool_evidence": ("tool_results",),
    "contract_constraints": (
        "constraints",
        "manager_product_policy_hints",
    ),
    "loop_control": (
        "round_index",
        "manager_loop_scope",
    ),
    "guard_repair": ("guard_feedback",),
}


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
    runtime_payload_layer_plan = _runtime_payload_layer_plan(dynamic_payload_keys)
    return {
        "contract_version": MANAGER_PROMPT_LAYER_CONTRACT_VERSION,
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
        },
        "provider_overlay_contract": {
            "owner": PROVIDER_OVERLAY_OWNER,
            "trace_only": True,
            "may_set_model": True,
            "may_set_transport": True,
            "may_change_system_contract": False,
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
        "progressive_disclosure": {
            "full_context_in_user_payload": True,
            "prompt_registry_trace_only": True,
            "provider_metadata_trace_only": True,
            "tool_results_dynamic_key": "tool_results",
            "manager_context_dynamic_keys": [
                "phase_a_current_turn_context",
                "phase_a_manager_context_pack",
                "manager_context_packet_v1",
            ],
        },
}


def _runtime_payload_layer_plan(dynamic_payload_keys: list[str]) -> dict[str, Any]:
    remaining = set(dynamic_payload_keys)
    sections: list[dict[str, Any]] = []
    for section_id in _RUNTIME_PAYLOAD_LAYER_ORDER:
        section_keys = [key for key in _RUNTIME_PAYLOAD_LAYER_KEYS[section_id] if key in remaining]
        remaining.difference_update(section_keys)
        sections.append(
            {
                "section_id": section_id,
                "owner": _runtime_payload_section_owner(section_id),
                "keys": section_keys,
            }
        )
    return {
        "suffix_order": list(_RUNTIME_PAYLOAD_LAYER_ORDER),
        "sections": sections,
        "uncategorized_dynamic_keys": sorted(remaining),
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


def _runtime_payload_section_owner(section_id: str) -> str:
    if section_id == "context_engineering":
        return "ManagerRuntime.ContextEngineering"
    if section_id == "tool_evidence":
        return "ManagerRuntime.ToolLoop"
    if section_id == "guard_repair":
        return "ManagerRuntime.Guard"
    return "ManagerRuntime"


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
