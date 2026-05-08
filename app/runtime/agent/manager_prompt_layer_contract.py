from __future__ import annotations

import hashlib
from typing import Any


MANAGER_PROMPT_LAYER_CONTRACT_VERSION = "manager_prompt_layer_contract.v1"
MANAGER_PROMPT_CACHE_PROFILE_ID = "manager_prompt_prefix_cache_profile.v1"


def build_manager_prompt_layer_contract(
    *,
    manager_loop_scope: str,
    system_prompt: str,
    user_payload: dict[str, Any],
) -> dict[str, Any]:
    dynamic_payload_keys = sorted(str(key) for key in user_payload)
    return {
        "contract_version": MANAGER_PROMPT_LAYER_CONTRACT_VERSION,
        "manager_loop_scope": str(manager_loop_scope),
        "system_prompt_layer": "static_prefix",
        "runtime_payload_layer": "dynamic_suffix",
        "provider_profile_layer": "transport_overlay_trace_only",
        "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
        "dynamic_payload_keys": dynamic_payload_keys,
        "prompt_cache_profile": {
            "profile_id": MANAGER_PROMPT_CACHE_PROFILE_ID,
            "static_prefix_first": True,
            "dynamic_context_last": True,
            "cache_metric_field": "usage.*.cached_tokens",
            "cache_truth_source": "provider_reported_usage_only",
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


__all__ = [
    "MANAGER_PROMPT_CACHE_PROFILE_ID",
    "MANAGER_PROMPT_LAYER_CONTRACT_VERSION",
    "build_manager_prompt_layer_contract",
]
