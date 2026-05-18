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
_READ_MODEL_BUDGET_FIELDS = (
    "status",
    "daily_target_kcal",
    "target_kcal",
    "consumed_kcal",
    "remaining_kcal",
    "show_macro",
    "macro_guard_reason",
)
_READ_MODEL_BODY_FIELDS = (
    "status",
    "daily_target_kcal",
    "tdee_kcal",
    "current_weight_kg",
    "target_weight_kg",
    "goal",
    "activity_level",
)
_EVIDENCE_MAP_FIELDS = (
    "status",
    "availability",
    "posture",
    "source_type",
    "match_posture",
    "commit_posture",
    "macro_evidence_status",
    "macro_display_status",
    "macro_guard_reason",
    "source_exactness",
    "selected_extract_status",
    "admissibility",
)
_EXTRACT_REFERENCE_FIELDS = (
    "packet_id",
    "source_type",
    "matched_record_ref",
    "match_posture",
    "serving_applicability",
    "kcal_basis",
    "macro_evidence_status",
    "source_exactness",
    "manager_allowed_use",
    "commit_posture",
    "admissibility",
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


def compact_read_model_summary_for_prompt(value: Any) -> dict[str, Any]:
    summary = dict(value or {}) if isinstance(value, dict) else {}
    compact: dict[str, Any] = {
        "read_model_summary_compact": True,
        "read_only": True,
        "mutation_authority": False,
    }
    budget = _select_present_fields(
        dict(summary.get("budget") or {}) if isinstance(summary.get("budget"), dict) else {},
        _READ_MODEL_BUDGET_FIELDS,
    )
    if budget:
        compact["budget"] = budget
    body_plan = _select_present_fields(
        dict(summary.get("body_plan") or {}) if isinstance(summary.get("body_plan"), dict) else {},
        _READ_MODEL_BODY_FIELDS,
    )
    if body_plan:
        compact["body_plan"] = body_plan
    current_day = dict(summary.get("current_day") or {}) if isinstance(summary.get("current_day"), dict) else {}
    if current_day:
        compact["current_day"] = _select_present_fields(
            current_day,
            ("open_workflow_type", "active_meal_thread_ref"),
        )
    recent_meals = summary.get("recent_committed_meals")
    if isinstance(recent_meals, list):
        compact["recent_committed_meal_count"] = len(recent_meals)
    return compact


def compact_evidence_state_for_prompt(value: Any) -> dict[str, Any]:
    state = dict(value or {}) if isinstance(value, dict) else {}
    compact: dict[str, Any] = {
        "evidence_state_compact": True,
        "read_only": True,
        "mutation_authority": False,
        "selection_owner": "manager",
    }
    for key in ("fooddb", "websearch", "macro"):
        section = _select_present_fields(
            dict(state.get(key) or {}) if isinstance(state.get(key), dict) else {},
            _EVIDENCE_MAP_FIELDS,
        )
        if section:
            compact[key] = section
    selected_extracts = state.get("selected_extracts")
    if isinstance(selected_extracts, list):
        compact["selected_extracts"] = [
            _select_present_fields(dict(item), _EXTRACT_REFERENCE_FIELDS)
            for item in selected_extracts[:5]
            if isinstance(item, dict)
        ]
        compact["selected_extract_count"] = len(selected_extracts)
    rejected_candidates = state.get("rejected_candidates")
    if isinstance(rejected_candidates, list):
        compact["rejected_candidate_count"] = len(rejected_candidates)
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
