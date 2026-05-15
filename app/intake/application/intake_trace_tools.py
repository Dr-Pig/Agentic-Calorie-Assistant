from __future__ import annotations

from typing import Any

from ...logging import now_iso
from ...runtime.infrastructure.trace.stage_trace_store import append_stage_trace_event
from .intake_tool_runtime import conversation_pending_followup, json_safe, normalize_live_payload

_normalize_intake_live_payload = normalize_live_payload


def append_trace_event_tool(
    *,
    request_id: str,
    stage: str,
    status: str,
    summary: dict[str, Any],
) -> None:
    append_stage_trace_event(
        request_id,
        {
            "request_id": request_id,
            "stage": stage,
            "status": status,
            "timestamp": now_iso(),
            "summary": json_safe(summary),
        },
    )


def resolve_correction_target_tool(
    *,
    resolved_state: Any,
) -> dict[str, Any]:
    target = ((resolved_state.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {}).copy()
    thread_candidates: list[dict[str, Any]] = []
    seen_thread_ids = set()
    if target.get("meal_thread_id") is not None:
        seen_thread_ids.add(target.get("meal_thread_id"))
        thread_candidates.append(
            {
                "meal_thread_id": target.get("meal_thread_id"),
                "meal_version_id": target.get("meal_version_id"),
                "meal_title": target.get("meal_title"),
                "target_resolution_source": target.get("target_resolution_source"),
                "source": "target_meal_reference",
                "mutation_authority": False,
                "selected_target": False,
            }
        )
    item_candidates = [
        dict(item) for item in (target.get("item_candidates") or []) if isinstance(item, dict)
    ]
    seen_candidate_ids = {
        item.get("meal_item_id") for item in item_candidates if item.get("meal_item_id") is not None
    }
    for meal in (resolved_state.injected_context or {}).get("RECENT_COMMITTED_MEALS_SUMMARY") or []:
        if not isinstance(meal, dict):
            continue
        meal_thread_id = meal.get("meal_thread_id")
        if meal_thread_id is not None and meal_thread_id not in seen_thread_ids:
            seen_thread_ids.add(meal_thread_id)
            thread_candidates.append(
                {
                    "meal_thread_id": meal_thread_id,
                    "meal_version_id": meal.get("meal_version_id"),
                    "meal_title": meal.get("meal_title"),
                    "total_kcal": meal.get("total_kcal"),
                    "source": "recent_committed_meal",
                    "mutation_authority": False,
                    "selected_target": False,
                }
            )
        for item in meal.get("item_candidates") or []:
            if not isinstance(item, dict):
                continue
            meal_item_id = item.get("meal_item_id")
            if meal_item_id in seen_candidate_ids:
                continue
            seen_candidate_ids.add(meal_item_id)
            item_candidates.append(
                {
                    **dict(item),
                    "meal_thread_id": meal.get("meal_thread_id"),
                    "meal_version_id": meal.get("meal_version_id"),
                    "source": "recent_committed_meal",
                    "mutation_authority": False,
                    "selected_target": False,
                }
            )
    if item_candidates:
        target["item_candidates"] = item_candidates
    if thread_candidates:
        target["thread_candidates"] = thread_candidates
    pending = conversation_pending_followup(getattr(resolved_state, "conversation_state", None))
    if pending.get("is_open"):
        target["target_resolution_source"] = "pending_followup_state"
        target["correction_confidence"] = "high"
    return target
