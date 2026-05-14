from __future__ import annotations

import json
from typing import Any


_CURRENT_BUDGET_VIEW_FIELDS = (
    "user_id",
    "local_date",
    "budget_kcal",
    "consumed_kcal",
    "remaining_kcal",
    "active_meal_count",
    "show_macro",
    "macro_guard_reason",
)
_CURRENT_BUDGET_MEAL_FIELDS = (
    "meal_thread_id",
    "meal_version_id",
    "meal_title",
    "total_kcal",
    "occurred_at",
    "resolution_status",
)
_ACTIVE_BODY_PLAN_VIEW_FIELDS = (
    "body_plan_id",
    "plan_status",
    "goal_type",
    "current_weight_kg",
    "target_weight_kg",
    "daily_budget_kcal",
    "recommended_target_kcal",
    "daily_deficit_kcal",
    "safety_floor_kcal",
    "estimated_tdee",
    "target_pace_kg_per_week",
    "plan_source",
    "profile_status",
)
_REMAINING_BUDGET_CONTRACT_FIELDS = (
    "status",
    "user_id",
    "local_date",
    "daily_target_kcal",
    "consumed_kcal",
    "remaining_kcal",
    "meal_count",
)
_CALIBRATION_PROPOSAL_FIELDS = (
    "proposal_container_id",
    "proposal_type",
    "proposal_status",
    "top_option_id",
    "created_at",
)


def compact_non_fooddb_read_model_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}

    current_budget = _object_mapping(evidence.get("current_budget_view"))
    if current_budget:
        compact["current_budget_view"] = _compact_current_budget_view(current_budget)

    active_body_plan = _object_mapping(evidence.get("active_body_plan_view"))
    if active_body_plan:
        compact["active_body_plan_view"] = _select_fields(
            active_body_plan,
            _ACTIVE_BODY_PLAN_VIEW_FIELDS,
        )

    remaining_budget = _object_mapping(evidence.get("remaining_budget_contract"))
    if remaining_budget:
        compact["remaining_budget_contract"] = _select_fields(
            remaining_budget,
            _REMAINING_BUDGET_CONTRACT_FIELDS,
        )

    if evidence.get("pending_proposal_status") not in (None, ""):
        compact["pending_proposal_status"] = _json_safe(evidence["pending_proposal_status"])
    if evidence.get("proposal_count") not in (None, ""):
        compact["proposal_count"] = _json_safe(evidence["proposal_count"])

    proposals = evidence.get("open_calibration_proposals")
    if isinstance(proposals, list):
        compact["open_calibration_proposals"] = [
            _select_fields(_object_mapping(item), _CALIBRATION_PROPOSAL_FIELDS)
            for item in proposals[:5]
        ]

    app_usage_policy = _object_mapping(evidence.get("app_usage_policy"))
    if app_usage_policy:
        compact["app_usage_policy"] = _json_safe(app_usage_policy)

    return {key: value for key, value in compact.items() if value not in (None, "", {}, [])}


def _compact_current_budget_view(view: dict[str, Any]) -> dict[str, Any]:
    compact = _select_fields(view, _CURRENT_BUDGET_VIEW_FIELDS)
    meals = view.get("meals")
    if isinstance(meals, list):
        compact["meals"] = [
            _select_fields(_object_mapping(meal), _CURRENT_BUDGET_MEAL_FIELDS)
            for meal in meals[:10]
        ]
    return compact


def _select_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: _json_safe(payload[key])
        for key in fields
        if payload.get(key) not in (None, "", {}, [])
    }


def _object_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    safe = _json_safe(value)
    return dict(safe) if isinstance(safe, dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))
