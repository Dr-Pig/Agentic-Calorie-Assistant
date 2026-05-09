from __future__ import annotations

from typing import Any

_PIN_REFERENCE_FIELDS = (
    "runtime_turn_id",
    "pending_question_id",
    "draft_id",
    "meal_thread_id",
    "meal_version_id",
    "meal_item_id",
    "expected_answer_type",
    "question",
    "pending_question",
)
_BUDGET_SUMMARY_REFERENCE_FIELDS = (
    "status",
    "daily_target_kcal",
    "budget_kcal",
    "target_kcal",
    "consumed_kcal",
    "remaining_kcal",
    "predicted_remaining_kcal_after",
    "overshoot_detected",
    "overshoot_kcal",
    "show_macro",
    "macro_guard_reason",
    "consumed_protein",
    "consumed_carbs",
    "consumed_fat",
)
_ACTIVE_MEAL_REFERENCE_FIELDS = (
    "meal_thread_id",
    "meal_version_id",
    "meal_item_id",
    "meal_title",
    "canonical_name",
    "display_name",
    "target_label",
)


def compact_hard_pins_after_tool_evidence(value: Any) -> dict[str, Any]:
    pins = dict(value or {}) if isinstance(value, dict) else {}
    compact: dict[str, Any] = {
        "hard_pins_compacted_after_tool_evidence": True,
        "read_only": True,
        "mutation_authority": False,
    }
    pending_followup = _select_present_fields(
        dict(pins.get("pending_followup") or {})
        if isinstance(pins.get("pending_followup"), dict)
        else {},
        _PIN_REFERENCE_FIELDS,
    )
    if pending_followup:
        compact["pending_followup"] = pending_followup
    pending_draft = _select_present_fields(
        dict(pins.get("pending_draft") or {}) if isinstance(pins.get("pending_draft"), dict) else {},
        _PIN_REFERENCE_FIELDS,
    )
    if pending_draft:
        compact["pending_draft"] = pending_draft
    last_question = pins.get("last_assistant_question")
    if last_question not in (None, "", {}, []):
        compact["last_assistant_question"] = last_question
    return compact


def compact_active_day_state_after_tool_evidence(value: Any) -> dict[str, Any]:
    state = dict(value or {}) if isinstance(value, dict) else {}
    compact: dict[str, Any] = {
        "active_day_state_compacted_after_tool_evidence": True,
        "read_only": True,
        "mutation_authority": False,
    }
    budget_summary = _select_present_fields(
        dict(state.get("budget_summary") or {})
        if isinstance(state.get("budget_summary"), dict)
        else {},
        _BUDGET_SUMMARY_REFERENCE_FIELDS,
    )
    if budget_summary:
        compact["budget_summary"] = budget_summary
    active_meal_ref = _compact_active_meal_thread_ref(state.get("active_meal_thread_ref"))
    if active_meal_ref:
        compact["active_meal_thread_ref"] = active_meal_ref
    correction_summary = state.get("recent_correction_removal_summary")
    if isinstance(correction_summary, list):
        compact["recent_correction_removal_count"] = len(correction_summary)
    return compact


def _compact_active_meal_thread_ref(value: Any) -> dict[str, Any]:
    meal_ref = dict(value or {}) if isinstance(value, dict) else {}
    compact = _select_present_fields(meal_ref, _ACTIVE_MEAL_REFERENCE_FIELDS)
    items = meal_ref.get("items")
    if isinstance(items, list):
        compact["item_count"] = len(items)
    item_candidates = meal_ref.get("item_candidates")
    if isinstance(item_candidates, list):
        compact["item_candidate_count"] = len(item_candidates)
    return compact


def _select_present_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload[key] for key in fields if payload.get(key) not in (None, "", {}, [])}
