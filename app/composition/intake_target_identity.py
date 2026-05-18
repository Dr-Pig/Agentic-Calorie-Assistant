from __future__ import annotations

from typing import Any


def manager_owned_evidence_base_dish(
    *,
    semantic_decision: dict[str, Any],
    target: dict[str, Any],
) -> str | None:
    """Choose the evidence lookup identity without taking semantic ownership."""

    target_name = str(target.get("canonical_name") or "").strip()
    validated_target_name = str(target.get("validated_canonical_name") or "").strip()
    if manager_selected_existing_target(target):
        if validated_target_name and _modifier_refinement_requested(semantic_decision):
            return validated_target_name
        if target_name:
            return target_name
    base_dish = str(semantic_decision.get("base_dish") or "").strip()
    return base_dish or target_name or None


def hydrate_manager_selected_target(target: dict[str, Any], resolved_state: Any | None) -> dict[str, Any]:
    if resolved_state is None or not manager_selected_existing_target(target):
        return target
    active_meal = _as_dict(getattr(resolved_state, "active_meal", None))
    if not active_meal or not _target_matches_active_meal(target, active_meal):
        return target
    hydrated = dict(target)
    canonical_name = str(active_meal.get("canonical_name") or active_meal.get("meal_title") or "").strip()
    if canonical_name:
        hydrated["validated_canonical_name"] = canonical_name
        hydrated["validated_canonical_name_source"] = "active_meal_target_identity"
        if not str(hydrated.get("canonical_name") or "").strip():
            hydrated["canonical_name"] = canonical_name
    for key in ("meal_thread_id", "meal_item_id"):
        if hydrated.get(key) in (None, "") and active_meal.get(key) not in (None, ""):
            hydrated[key] = active_meal.get(key)
    return hydrated


def manager_selected_existing_target(target: dict[str, Any]) -> bool:
    operation = str(target.get("operation") or target.get("action_type") or "").strip()
    target_object_type = str(target.get("target_object_type") or "").strip()
    return (
        operation in {"attach_to_pending_followup", "attach_to_active_meal"}
        or target_object_type in {"meal_thread", "meal_item"}
        or any(
            target.get(key) not in (None, "")
            for key in (
                "meal_thread_id",
                "meal_item_id",
                "target_meal_id",
                "source_meal_id",
                "target_object_id",
            )
        )
    )


def _modifier_refinement_requested(semantic_decision: dict[str, Any]) -> bool:
    if str(semantic_decision.get("size_hint") or "").strip():
        return True
    modifier_hints = semantic_decision.get("modifier_hints")
    return isinstance(modifier_hints, list) and any(str(item or "").strip() for item in modifier_hints)


def _target_matches_active_meal(target: dict[str, Any], active_meal: dict[str, Any]) -> bool:
    if not target:
        return False
    operation = str(target.get("operation") or target.get("action_type") or "").strip()
    if operation == "attach_to_pending_followup":
        return any(
            active_meal.get(key) not in (None, "")
            for key in ("meal_thread_id", "meal_item_id", "canonical_name", "meal_title")
        )
    target_ids = {
        value
        for key in ("meal_thread_id", "meal_item_id", "target_meal_id", "source_meal_id")
        if (value := target.get(key)) not in (None, "")
    }
    active_ids = {
        value
        for key in ("meal_thread_id", "meal_item_id")
        if (value := active_meal.get(key)) not in (None, "")
    }
    if target_ids and active_ids and _any_id_intersection(target_ids, active_ids):
        return True
    target_object_id = target.get("target_object_id")
    target_object_type = str(target.get("target_object_type") or "").strip()
    if target_object_id not in (None, ""):
        if target_object_type in {"", "meal_thread"} and _ids_equal(target_object_id, active_meal.get("meal_thread_id")):
            return True
        if target_object_type == "meal_item" and _ids_equal(target_object_id, active_meal.get("meal_item_id")):
            return True
    return False


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _any_id_intersection(left: set[Any], right: set[Any]) -> bool:
    return any(_ids_equal(left_item, right_item) for left_item in left for right_item in right)


def _ids_equal(left: Any, right: Any) -> bool:
    if left in (None, "") or right in (None, ""):
        return False
    return str(left) == str(right)


__all__ = [
    "hydrate_manager_selected_target",
    "manager_owned_evidence_base_dish",
    "manager_selected_existing_target",
]
