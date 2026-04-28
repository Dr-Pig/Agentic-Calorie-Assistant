from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ...database import get_or_create_user
from ...logging import now_iso
from ...nutrition.application.evidence_eligibility import classify_query_family, is_high_variance_family
from ...nutrition.application.estimate_artifacts import (
    EstimatedNutritionArtifact,
    build_exact_item_artifact,
    build_shadow_stub_artifact,
    shadow_stub_estimate_enabled,
)
from ...nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from ...runtime.infrastructure.trace.stage_trace_store import append_stage_trace_event
from ...shared.contracts.intake import EstimatePayload
from ...shared.time_labels import resolve_local_attribution
from .commit_service import persist_text_meal_payload
from .intake_tool_runtime import (
    PersistMealLogResult,
    conversation_pending_followup,
    json_safe,
    looks_like_multi_item_input,
    normalize_live_payload,
)


def read_body_plan_tool(db: Session, *, user_id: int) -> Any:
    from ...body.application import build_active_body_plan_view

    return build_active_body_plan_view(db, user_id=user_id)


def read_day_budget_tool(db: Session, *, user_id: int, local_date: str) -> Any:
    from ...budget.application import build_current_budget_view

    return build_current_budget_view(db, user_id=user_id, local_date=local_date)


def read_active_meal_tool(db: Session, *, user_id: int, local_date: str) -> dict[str, Any] | None:
    budget = read_day_budget_tool(db, user_id=user_id, local_date=local_date)
    if not budget.meals:
        return None
    latest_meal = max(
        budget.meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
    )
    return {
        "meal_thread_id": latest_meal.meal_thread_id,
        "meal_version_id": latest_meal.meal_version_id,
        "meal_title": latest_meal.meal_title,
        "total_kcal": latest_meal.total_kcal,
    }


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
    pending = conversation_pending_followup(getattr(resolved_state, "conversation_state", None))
    if pending.get("is_open"):
        target["target_resolution_source"] = "pending_followup_state"
        target["correction_confidence"] = "high"
    return target


def compare_against_budget_tool(
    *,
    current_budget_view: Any,
    estimated_kcal: int,
    replaced_kcal: int = 0,
) -> dict[str, Any]:
    consumed_before = int(current_budget_view.consumed_kcal or 0)
    budget_kcal = int(current_budget_view.budget_kcal or 0)
    predicted_consumed = max(consumed_before - max(int(replaced_kcal or 0), 0), 0) + max(int(estimated_kcal or 0), 0)
    predicted_remaining = budget_kcal - predicted_consumed
    return {
        "budget_kcal": budget_kcal,
        "consumed_kcal_before": consumed_before,
        "replaced_kcal_before": max(int(replaced_kcal or 0), 0),
        "predicted_consumed_kcal_after": predicted_consumed,
        "predicted_remaining_kcal_after": predicted_remaining,
        "overshoot_detected": predicted_remaining < 0,
        "overshoot_kcal": abs(min(predicted_remaining, 0)),
    }


def _fill_missing_trace_dates(payload: EstimatePayload) -> None:
    trace_contract = dict(payload.trace_contract or {})
    if str(trace_contract.get("local_date") or "").strip():
        payload.trace_contract = trace_contract
        return
    attribution = resolve_local_attribution(
        trace_contract.get("occurred_at"),
        timezone_name=str(trace_contract.get("timezone") or "") or None,
    )
    if attribution.get("occurred_at") is not None:
        trace_contract["occurred_at"] = attribution["occurred_at"]
    if str(attribution.get("occurred_at_utc") or "").strip():
        trace_contract["occurred_at_utc"] = attribution["occurred_at_utc"]
    if str(attribution.get("occurred_at_local") or "").strip():
        trace_contract["occurred_at_local"] = attribution["occurred_at_local"]
    if str(attribution.get("local_date") or "").strip():
        trace_contract["local_date"] = attribution["local_date"]
    if str(attribution.get("timezone") or "").strip():
        trace_contract["timezone"] = attribution["timezone"]
    trace_contract.setdefault("search_attempt_count", 0)
    trace_contract.setdefault("grounding_summary", {"exact_truth_present": False, "retrieved_knowledge_count": 0, "evidence_roles": []})
    trace_contract.setdefault("reasoning_state", {"exact_lane_count": 0, "search_attempt_count": 0})
    payload.trace_contract = trace_contract


async def estimate_nutrition_tool(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    request_id: str,
    local_date: str,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_adapter: Any | None = None,
    allow_search: bool = True,
    force_new_meal_context: bool = False,
    contextualized_query: str | None = None,
) -> EstimatedNutritionArtifact:
    active_provider = manager_provider or provider
    exact_packet = build_exact_item_lane_packet(raw_user_input, limit=3)
    top_exact_candidate = exact_packet.get("top_exact_candidate")
    if isinstance(top_exact_candidate, dict) and not looks_like_multi_item_input(raw_user_input):
        artifact = build_exact_item_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            exact_candidate=top_exact_candidate,
        )
        normalize_live_payload(artifact.payload, raw_user_input=raw_user_input)
        return artifact

    if shadow_stub_estimate_enabled(provider=active_provider):
        return build_shadow_stub_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
        )

    artifact = build_shadow_stub_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date or datetime.now().date().isoformat(),
    )
    if force_new_meal_context:
        if hasattr(artifact.runtime_context, "latest_log"):
            artifact.runtime_context.latest_log = None
        if hasattr(artifact.runtime_context, "conversation_state"):
            conversation_state = getattr(artifact.runtime_context, "conversation_state")
            if conversation_state is not None and hasattr(conversation_state, "pending_followup_state"):
                pending_state = getattr(conversation_state, "pending_followup_state")
                if pending_state is not None and hasattr(pending_state, "is_open"):
                    pending_state.is_open = False
    _fill_missing_trace_dates(artifact.payload)
    normalize_live_payload(
        artifact.payload,
        raw_user_input=raw_user_input,
        family_rule=classify_query_family(raw_user_input),
        high_variance=is_high_variance_family(raw_user_input),
    )
    return artifact


def persist_meal_log_tool(
    db: Session,
    *,
    artifact: EstimatedNutritionArtifact,
    request_id: str,
) -> PersistMealLogResult:
    user = artifact.runtime_context.user or get_or_create_user(db, artifact.request.user_id)
    decision = persist_text_meal_payload(
        db=db,
        user=user,
        latest_log=artifact.runtime_context.latest_log,
        planner_intent=artifact.planner_result.intent,
        payload=artifact.payload,
        raw_input=artifact.request.text,
        request_id=request_id,
        incoming_user_message_id=artifact.runtime_context.incoming_user_message_id,
        conversation_state=artifact.runtime_context.conversation_state,
        planner_result=artifact.planner_result,
    )
    return PersistMealLogResult(
        action=str(decision.get("action") or "noop"),
        status=decision.get("status"),
        persisted_log_id=decision.get("persisted_log_id"),
        linked_meal_log_id=decision.get("linked_meal_log_id"),
        canonical_commit=decision.get("canonical_commit"),
    )
