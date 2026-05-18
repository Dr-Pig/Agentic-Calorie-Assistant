from __future__ import annotations

import hashlib
import json
from typing import Any

PROVIDER_OVERLAY_OWNER = "ProviderAdapter"


def build_manager_prompt_trace_fields(
    *,
    system_prompt_version: str,
    system_section_contract: dict[str, Any],
    user_payload: dict[str, Any],
    tool_surface_keys: tuple[str, ...],
) -> dict[str, Any]:
    constraints = user_payload.get("constraints")
    constraints_payload = constraints if isinstance(constraints, dict) else {}
    return {
        "manager_prompt_version": str(system_prompt_version),
        "prompt_section_hashes": dict(system_section_contract["section_sha256"]),
        "tool_schema_hash": _hash_payload(
            {
                "available_tools": user_payload.get("available_tools"),
                "tool_surface_keys": tool_surface_keys,
            }
        ),
        "output_schema_hash": _hash_payload(
            {
                "schema_name": constraints_payload.get("manager_contract_schema_name"),
                "schema_version": constraints_payload.get("manager_contract_schema_version"),
                "transport_policy": constraints_payload.get("manager_contract_transport_policy"),
            }
        ),
        "provider_profile": {
            "owner": PROVIDER_OVERLAY_OWNER,
            "profile_id": constraints_payload.get("manager_contract_provider_profile_id"),
            "semantic_overlay_allowed": False,
        },
        "cached_tokens": "unknown",
    }


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            default=str,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


__all__ = ["PROVIDER_OVERLAY_OWNER", "build_manager_prompt_trace_fields"]
