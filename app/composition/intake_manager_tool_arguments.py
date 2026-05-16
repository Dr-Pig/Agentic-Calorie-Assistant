from __future__ import annotations

from typing import Any

_MANAGER_SEMANTIC_TOOL_ARGUMENT_KEYS = (
    "base_dish",
    "aliases",
    "brand_hint",
    "size_hint",
    "modifier_hints",
    "listed_items",
    "retrieval_goal",
    "semantic_authority_source",
)


def manager_semantic_decision_argument_payload(arguments: dict[str, Any] | None) -> dict[str, Any]:
    source = dict(arguments or {})
    nested = source.get("manager_semantic_decision")
    raw = dict(nested) if isinstance(nested, dict) and nested else {}
    if not raw:
        raw = {
            key: source.get(key)
            for key in _MANAGER_SEMANTIC_TOOL_ARGUMENT_KEYS
            if key in source
        }
    if raw and not str(raw.get("semantic_authority_source") or "").strip():
        raw["semantic_authority_source"] = "manager_tool_arguments"
    return raw


__all__ = ["manager_semantic_decision_argument_payload"]
