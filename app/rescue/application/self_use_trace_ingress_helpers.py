from __future__ import annotations

import re
from hashlib import sha256
from typing import Any, Mapping

from app.rescue.application.self_use_trace_ingress_contracts import REQUIRED_SCOPE_KEYS


SECRET_VALUE_RE = re.compile(r"(?i)sk-(?:live|test)-[A-Za-z0-9_-]+")


def current_budget_view(trace: Mapping[str, Any]) -> dict[str, Any]:
    context = mapping(trace.get("context_snapshot"))
    active_day = mapping(context.get("active_day_state"))
    budget = mapping(active_day.get("budget_summary"))
    source = "context_snapshot.active_day_state.budget_summary"
    if not budget:
        budget = mapping(context.get("current_budget_view"))
        source = "context_snapshot.current_budget_view"
    if not budget:
        budget = mapping(trace.get("today_summary"))
        source = "today_summary"
    base = int_or_none(budget.get("base_budget_kcal") or budget.get("budget_kcal"))
    effective = int_or_none(budget.get("effective_budget_kcal") or base)
    consumed = int_or_none(
        budget.get("meal_consumption_total_kcal") or budget.get("consumed_kcal")
    )
    return {
        "local_date": str(
            dig(trace, "trace_meta", "local_date")
            or dig(trace, "request", "local_date")
            or ""
        ),
        "base_budget_kcal": base,
        "effective_budget_kcal": effective,
        "meal_consumption_total_kcal": consumed,
        "remaining_kcal": int_or_none(budget.get("remaining_kcal")),
        "source": source,
    }


def recent_committed_meals_view(trace: Mapping[str, Any]) -> dict[str, Any]:
    context = mapping(trace.get("context_snapshot"))
    raw_meals = context.get("meal_threads") or trace.get("meal_threads") or []
    meals = [meal_view(item) for item in raw_meals if isinstance(item, Mapping)]
    meals = [item for item in meals if item["meal_thread_id"] or item["meal_title"]]
    return {"meal_count": len(meals), "meals": meals}


def active_body_plan_view(trace: Mapping[str, Any]) -> dict[str, Any]:
    context = mapping(trace.get("context_snapshot"))
    plan = mapping(context.get("active_body_plan") or trace.get("active_body_plan"))
    return {
        "safety_floor_kcal": int_or_none(plan.get("safety_floor_kcal")),
        "target_days": list(plan.get("target_days") or []),
        "source": "context_snapshot.active_body_plan" if plan else "missing",
    }


def source_refs(
    *,
    request_id: str,
    context_snapshot: Mapping[str, Any],
    current_budget: Mapping[str, Any],
    recent_meals: Mapping[str, Any],
    active_body_plan: Mapping[str, Any],
) -> list[dict[str, str]]:
    refs = [
        {
            "source_type": "runtime_request_trace",
            "source_id": request_id,
            "field_path": "trace_meta.request_id",
        }
    ]
    if context_snapshot:
        refs.append(
            {
                "source_type": "manager_context_packet",
                "source_id": request_id,
                "field_path": "context_snapshot",
            }
        )
    if current_budget.get("source"):
        refs.append(
            {
                "source_type": "current_budget_view",
                "source_id": request_id,
                "field_path": str(current_budget["source"]),
            }
        )
    for meal in recent_meals.get("meals") or []:
        refs.append(
            {
                "source_type": "meal_thread",
                "source_id": str(meal.get("meal_thread_id") or ""),
                "field_path": "context_snapshot.meal_threads",
            }
        )
    if active_body_plan.get("source") != "missing":
        refs.append(
            {
                "source_type": "active_body_plan",
                "source_id": request_id,
                "field_path": str(active_body_plan["source"]),
            }
        )
    return refs


def scope_keys(trace: Mapping[str, Any], overrides: Mapping[str, str]) -> dict[str, str]:
    trace_meta = mapping(trace.get("trace_meta"))
    request = mapping(trace.get("request"))
    lab_scope = mapping(trace.get("rescue_lab_scope"))
    return {
        "user_id": str(
            overrides.get("user_id")
            or lab_scope.get("user_id")
            or trace_meta.get("user_id")
            or request.get("user_id")
            or ""
        ),
        "workspace_id": str(
            overrides.get("workspace_id") or lab_scope.get("workspace_id") or ""
        ),
        "project_id": str(
            overrides.get("project_id") or lab_scope.get("project_id") or ""
        ),
        "surface": str(overrides.get("surface") or lab_scope.get("surface") or ""),
        "run_id": str(
            overrides.get("run_id") or lab_scope.get("run_id") or trace_meta.get("run_id") or ""
        ),
    }


def sanitize(value: Any, path: str = "") -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        fields: list[str] = []
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            redacted, child_fields = sanitize(item, child_path)
            result[key] = redacted
            fields.extend(child_fields)
        return result, fields
    if isinstance(value, list):
        result_list: list[Any] = []
        fields = []
        for index, item in enumerate(value):
            redacted, child_fields = sanitize(item, f"{path}[{index}]")
            result_list.append(redacted)
            fields.extend(child_fields)
        return result_list, fields
    if isinstance(value, str) and SECRET_VALUE_RE.search(value):
        return SECRET_VALUE_RE.sub("[REDACTED]", value), [path]
    return value, []


def request_id(trace: Mapping[str, Any]) -> str:
    return str(dig(trace, "trace_meta", "request_id") or trace.get("request_id") or "unknown-request")


def event_id(scope: Mapping[str, str], resolved_request_id: str) -> str:
    raw = "|".join(scope[key] for key in REQUIRED_SCOPE_KEYS) + f"|{resolved_request_id}"
    return "rescue-ingress-" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def meal_view(item: Mapping[str, Any]) -> dict[str, Any]:
    active_version = mapping(item.get("active_version"))
    return {
        "meal_thread_id": str(item.get("meal_thread_id") or item.get("id") or ""),
        "meal_title": str(item.get("meal_title") or item.get("title") or ""),
        "total_kcal": int_or_none(active_version.get("total_kcal") or item.get("total_kcal")),
    }


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def dig(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
