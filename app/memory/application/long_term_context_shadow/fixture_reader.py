from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import (
    CHAT_TRACE_SECTION_ALIASES,
    DOGFOOD_EXPORT_SECTIONS,
)
from app.memory.application.long_term_context_shadow.utils import (
    _list_of_dicts,
    _normalize_datetime,
    _parse_datetime,
    _trace_id,
)
from app.memory.domain.summaries import CommittedMealEvent


def _normalize_dogfood_export_payload(
    fixture_payload: dict[str, Any],
) -> dict[str, Any]:
    root = dict(fixture_payload or {})
    export_root, source_shape = _dogfood_export_root(root)
    fixture = dict(root)

    normalized_sections: list[str] = []
    for section in DOGFOOD_EXPORT_SECTIONS:
        if section in export_root:
            fixture[section] = export_root[section]
            normalized_sections.append(section)

    if "conversation_history_summaries" not in fixture:
        for alias in CHAT_TRACE_SECTION_ALIASES:
            if alias in export_root:
                fixture["conversation_history_summaries"] = export_root[alias]
                normalized_sections.append("conversation_history_summaries")
                break

    fixture["_input_reader"] = {
        "source_shape": source_shape,
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "real_dogfood_export_claim_ignored": source_shape != "top_level_fixture",
        "normalized_sections": sorted(set(normalized_sections)),
        "supported_sections": list(DOGFOOD_EXPORT_SECTIONS) + ["chat_trace_metadata"],
        "direct_db_access_used": False,
        "live_provider_called": False,
    }
    return fixture


def _dogfood_export_root(root: dict[str, Any]) -> tuple[dict[str, Any], str]:
    for key in ("dogfood_export", "dogfood_exports", "exports", "export"):
        value = root.get(key)
        if isinstance(value, dict):
            return dict(value), key
    return root, "top_level_fixture"


def _committed_meal_events(fixture: dict[str, Any]) -> list[CommittedMealEvent]:
    events: list[CommittedMealEvent] = []
    for meal in _list_of_dicts(fixture.get("meal_logs")):
        occurred_at = _parse_datetime(meal.get("logged_at"))
        if occurred_at is None:
            continue
        occurred_at = _normalize_datetime(occurred_at)
        events.append(
            CommittedMealEvent(
                event_id=str(meal.get("meal_id") or _trace_id(meal)),
                occurred_at=occurred_at,
                item_names=[str(item) for item in meal.get("item_names") or []],
                store_name=(
                    str(meal.get("store_name")) if meal.get("store_name") else None
                ),
                cuisine_family=(
                    str(meal.get("cuisine_family"))
                    if meal.get("cuisine_family")
                    else None
                ),
            )
        )
    return events


def _source_section_counts(fixture: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for section in DOGFOOD_EXPORT_SECTIONS:
        value = fixture.get(section)
        if isinstance(value, list):
            counts[section] = len(value)
        elif isinstance(value, dict):
            counts[section] = 1
        else:
            counts[section] = 0
    return counts
