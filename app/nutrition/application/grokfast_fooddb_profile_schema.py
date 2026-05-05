from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


GROKFAST_FOODDB_PROFILE_SCHEMA_NAME = "grokfast_fooddb_packet_pass2_profile"
GROKFAST_FOODDB_PROFILE_SCHEMA_VERSION = "v1"


def is_grokfast_fooddb_profile_constraints(constraints: dict[str, Any] | None) -> bool:
    return (constraints or {}).get("fooddb_packet_smoke") is True


def build_grokfast_fooddb_profile_schema(
    *,
    stage: str,
    base_schema: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a diagnostic-only FoodDB packet schema overlay.

    The shared B1 pass-2 schema intentionally stays broader for existing Manager
    branches. This overlay only narrows the GrokFast FoodDB packet seam.
    """

    if stage != MANAGER_LOOP_STAGE or not isinstance(base_schema, dict):
        return deepcopy(base_schema) if isinstance(base_schema, dict) else None
    schema = deepcopy(base_schema)
    if not is_grokfast_fooddb_profile_constraints(constraints):
        return schema

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return schema

    properties.pop("evidence_used", None)
    required = _required_list(schema)
    if (constraints or {}).get("fooddb_packet_requires_item_results") is True:
        _append_required(required, "item_results")
    schema["required"] = required
    schema["x-diagnostic-profile"] = {
        "profile_schema_name": GROKFAST_FOODDB_PROFILE_SCHEMA_NAME,
        "profile_schema_version": GROKFAST_FOODDB_PROFILE_SCHEMA_VERSION,
        "top_level_evidence_used_allowed": False,
        "top_level_item_results_required": (constraints or {}).get(
            "fooddb_packet_requires_item_results"
        )
        is True,
        "shared_manager_schema_changed": False,
    }
    return schema


def profile_schema_transport_meta() -> dict[str, Any]:
    return {
        "schema_name": GROKFAST_FOODDB_PROFILE_SCHEMA_NAME,
        "schema_version": GROKFAST_FOODDB_PROFILE_SCHEMA_VERSION,
        "fooddb_profile_schema_applied": True,
        "shared_manager_schema_changed": False,
    }


def _required_list(schema: dict[str, Any]) -> list[str]:
    required = schema.get("required")
    if not isinstance(required, list):
        return []
    return [str(item) for item in required if isinstance(item, str)]


def _append_required(required: list[str], field: str) -> None:
    if field not in required:
        required.append(field)


__all__ = [
    "GROKFAST_FOODDB_PROFILE_SCHEMA_NAME",
    "GROKFAST_FOODDB_PROFILE_SCHEMA_VERSION",
    "build_grokfast_fooddb_profile_schema",
    "is_grokfast_fooddb_profile_constraints",
    "profile_schema_transport_meta",
]
