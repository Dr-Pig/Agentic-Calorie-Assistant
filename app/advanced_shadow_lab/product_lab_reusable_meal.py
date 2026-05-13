from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.reusable_meal_intake_shadow_retrieval import (
    build_reusable_meal_intake_shadow_retrieval,
)


def run_product_lab_reusable_meal_search(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    memory_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    scope_keys = {
        "user_id": str(turn.get("user_id") or fixture_inputs.get("user_id") or ""),
        "workspace_id": str(
            turn.get("workspace_id") or fixture_inputs.get("workspace_id") or ""
        ),
        "surface": str(turn.get("surface") or fixture_inputs.get("surface") or ""),
    }
    return build_reusable_meal_intake_shadow_retrieval(
        scope_keys=scope_keys,
        intake_signal=_mapping(fixture_inputs.get("reusable_meal_intake_signal")),
        reusable_meal_entities=[
            item
            for item in fixture_inputs.get("reusable_meal_entities") or []
            if isinstance(item, Mapping)
        ],
        memory_summary=memory_summary,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_reusable_meal_search"]
