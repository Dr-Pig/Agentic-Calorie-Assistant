from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.serialization import _list_of_dicts


def _trace_refs(fixture: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for item in _list_of_dicts(fixture.get("trace_metadata")):
        trace_id = item.get("trace_id")
        source_ref = item.get("source_object_ref")
        if trace_id and source_ref:
            refs[str(trace_id)] = str(source_ref)
    return refs


def _source_refs_for_meals(
    meals: list[dict[str, Any]], trace_refs: dict[str, str]
) -> list[str]:
    return [
        _source_ref(
            meal, trace_refs, fallback_kind="MealThread", fallback_id_key="meal_id"
        )
        for meal in meals
    ]


def _source_refs_matching(
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
    key: str,
    value: str,
) -> list[str]:
    return _source_refs_for_meals(
        [
            meal
            for meal in meals
            if value in [str(item) for item in meal.get(key) or []]
        ],
        trace_refs,
    )


def _trace_ids_matching(meals: list[dict[str, Any]], key: str, value: str) -> list[str]:
    return [
        _trace_id(meal)
        for meal in meals
        if value in [str(item) for item in meal.get(key) or []]
    ]


def _source_ref(
    item: dict[str, Any],
    trace_refs: dict[str, str],
    *,
    fallback_kind: str,
    fallback_id_key: str,
) -> str:
    trace_id = _trace_id(item)
    if trace_id in trace_refs:
        return trace_refs[trace_id]
    fallback_id = str(item.get(fallback_id_key) or trace_id)
    return f"{fallback_kind}:{fallback_id}"


def _trace_id(item: dict[str, Any]) -> str:
    return str(item.get("trace_id") or item.get("id") or "fixture-trace")
