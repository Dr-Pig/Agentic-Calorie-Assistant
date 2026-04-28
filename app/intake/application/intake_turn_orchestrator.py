from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from ...budget.application.current_budget_answer import build_remaining_budget_answer_contract
from ...body.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from ...runtime.agent.manager import IntakeManagerResult
from ...runtime.application.execution_guard import validate_onboarding_seed
from ...runtime.application.manager_service import run_intake_manager
from ...runtime.application.reply_renderer import render_bundle1_reply
from ...runtime.application.request_trace_artifacts import build_trace_refs, write_bundle1_request_trace_artifact
from ...runtime.application.sidecar_service import build_deterministic_sidecar
from ...runtime.application.state_resolver import resolve_v2_bundle1_state
from . import manager_tools as tools
from .intake_turn_support import normalized_activity_level, resolve_local_date


@dataclass(frozen=True)
class V2Bundle1OnboardingPayload:
    sex: str
    age_years: int
    height_cm: float
    current_weight_kg: float
    goal_type: str
    weekly_target_rate_kg: float
    timezone: str = "UTC"
    target_weight_kg: float | None = None
    activity_level: str | None = None
    daily_lifestyle: str | None = None
    weekly_exercise_days_band: str | None = None


def _record_timing(stage_timings: list[dict[str, Any]], stage: str, duration_ms: int) -> None:
    stage_timings.append({"stage": stage, "duration_ms": duration_ms})


async def execute_bundle1_turn(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str | None,
    onboarding_payload: V2Bundle1OnboardingPayload | None,
    local_date: str | None,
    allow_search: bool,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_adapter: Any | None = None,
    _timing_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_id = uuid4().hex
    stage_timings: list[dict[str, Any]] = []
    resolved_local_date = resolve_local_date(local_date)
    active_manager_provider = manager_provider or provider

    stage_start = int(time.time() * 1000)
    state_before = resolve_v2_bundle1_state(
        db,
        user_external_id=user_external_id,
        local_date=resolved_local_date,
    )
    _record_timing(stage_timings, "state_resolution", int(time.time() * 1000) - stage_start)

    stage_start = int(time.time() * 1000)
    manager_decision: IntakeManagerResult = await run_intake_manager(
        provider=active_manager_provider,
        raw_user_input=raw_user_input or "",
        onboarding_payload=onboarding_payload.__dict__ if onboarding_payload is not None else None,
        resolved_state=state_before,
        available_tools=("read_body_plan", "read_day_budget"),
    )
    manager_decision_ms = int(time.time() * 1000) - stage_start
    _record_timing(stage_timings, "manager_decision", manager_decision_ms)
    tools.append_trace_event_tool(
        request_id=request_id,
        stage="v2_manager_decision",
        status="ok",
        summary={
            "intent_type": manager_decision.intent_type,
            "workflow_effect": manager_decision.workflow_effect,
            "tool_calls": list(manager_decision.tool_calls),
            "llm_used": manager_decision.llm_used,
            "duration_ms": manager_decision_ms,
        },
    )

    onboarding_result = None
    remaining_budget = None
    nutrition_artifact = None
    persistence_result = None
    state_mutation_summary: dict[str, Any] = {
        "body_plan_seeded": False,
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
    }

    if manager_decision.intent_type == "complete_onboarding":
        if onboarding_payload is None:
            raise ValueError("Structured onboarding payload is required for complete_onboarding.")
        user = tools.get_or_create_user(db, user_external_id)
        onboarding_result = bootstrap_body_plan_for_date(
            db,
            user=user,
            inputs=OnboardingBootstrapInput(
                sex=onboarding_payload.sex,
                age_years=onboarding_payload.age_years,
                height_cm=onboarding_payload.height_cm,
                current_weight_kg=onboarding_payload.current_weight_kg,
                activity_level=normalized_activity_level(onboarding_payload.activity_level),
                daily_lifestyle=onboarding_payload.daily_lifestyle,
                weekly_exercise_days_band=onboarding_payload.weekly_exercise_days_band,
                goal_type=onboarding_payload.goal_type,
                weekly_target_rate_kg=onboarding_payload.weekly_target_rate_kg,
                target_weight_kg=onboarding_payload.target_weight_kg,
                local_date=resolved_local_date,
                timezone=onboarding_payload.timezone,
            ),
        )
        guard = validate_onboarding_seed(
            recommended_target_kcal=onboarding_result.target_result.recommended_target_kcal,
            safety_floor_kcal=onboarding_result.target_result.safety_floor_kcal,
        )
        if not guard.ok:
            raise ValueError(f"Bundle 1 onboarding guard failed: {', '.join(guard.violations)}")
        state_mutation_summary["body_plan_seeded"] = True
        tools.append_trace_event_tool(
            request_id=request_id,
            stage="v2_onboarding_seed",
            status="ok",
            summary={
                "daily_budget_kcal": onboarding_result.target_result.recommended_target_kcal,
                "estimated_tdee_kcal": onboarding_result.target_result.estimated_tdee_kcal,
                "safety_floor_kcal": onboarding_result.target_result.safety_floor_kcal,
            },
        )
    elif manager_decision.intent_type == "answer_remaining_budget":
        remaining_budget = build_remaining_budget_answer_contract(
            db,
            user_id=state_before.user_id,
            local_date=resolved_local_date,
        )
        tools.append_trace_event_tool(
            request_id=request_id,
            stage="v2_remaining_budget_read",
            status="ok",
            summary={
                "status": remaining_budget.status,
                "daily_target_kcal": remaining_budget.daily_target_kcal,
                "consumed_kcal": remaining_budget.consumed_kcal,
                "remaining_kcal": remaining_budget.remaining_kcal,
                "meal_count": remaining_budget.meal_count,
            },
        )
    elif manager_decision.intent_type == "onboarding_required":
        remaining_budget = build_remaining_budget_answer_contract(
            db,
            user_id=state_before.user_id,
            local_date=resolved_local_date,
        )
        tools.append_trace_event_tool(
            request_id=request_id,
            stage="v2_onboarding_required",
            status="ok",
            summary={
                "status": remaining_budget.status,
                "reason": "budget_query_without_active_plan",
            },
        )
    elif manager_decision.intent_type == "log_meal":
        if not raw_user_input or not raw_user_input.strip():
            raise ValueError("raw_user_input is required for Bundle 1 intake logging.")
        from .intake_execution_orchestrator import process_bundle2_intake

        return await process_bundle2_intake(
            db=db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=resolved_local_date,
            allow_search=allow_search,
            manager_provider=manager_provider,
            provider=provider,
            search_adapter=search_adapter,
            state_before=state_before,
            manager_decision=manager_decision,
            request_id=request_id,
            stage_timings=stage_timings,
        )
    else:
        raise ValueError(f"Unsupported Bundle 1 intent_type: {manager_decision.intent_type}")

    state_after = resolve_v2_bundle1_state(
        db,
        user_external_id=user_external_id,
        local_date=resolved_local_date,
    )
    if remaining_budget is None:
        remaining_budget = build_remaining_budget_answer_contract(
            db,
            user_id=state_after.user_id,
            local_date=resolved_local_date,
        )

    assistant_message = render_bundle1_reply(
        intent_type=manager_decision.intent_type,
        onboarding_result=onboarding_result,
        remaining_budget=remaining_budget,
        active_body_plan_view=state_after.active_body_plan_view,
        nutrition_payload=None,
        persistence_result=persistence_result,
        manager_final_action=None,
        budget_summary=None,
    )
    trace_summary = {
        "request_id": request_id,
        "manager_intent": manager_decision.intent_type,
        "tool_calls": list(manager_decision.tool_calls),
        "llm_used": manager_decision.llm_used,
    }
    sidecar = build_deterministic_sidecar(
        active_body_plan_view=state_after.active_body_plan_view,
        current_budget_view=state_after.current_budget_view,
        state_mutation_summary=state_mutation_summary,
        trace_summary=trace_summary,
        overshoot_summary=None,
    )
    tools.append_trace_event_tool(
        request_id=request_id,
        stage="v2_renderer_sidecar",
        status="ok",
        summary={
            "assistant_message": assistant_message,
            "state_delta": state_mutation_summary,
        },
    )

    latency_tracking = {
        "intent_type": manager_decision.intent_type,
        "tools_used": [
            (tc.get("tool_name") or tc.get("name", "unknown")) if isinstance(tc, dict) else str(tc)
            for tc in manager_decision.tool_calls
        ],
        "total_duration_ms": sum(st["duration_ms"] for st in stage_timings),
        "slowest_step_ms": max((st["duration_ms"] for st in stage_timings), default=0),
        "slowest_step_name": max(stage_timings, key=lambda x: x["duration_ms"])["stage"] if stage_timings else "none",
        "stage_timings": stage_timings,
    }

    write_bundle1_request_trace_artifact(
        request_id=request_id,
        user_external_id=user_external_id,
        local_date=resolved_local_date,
        raw_user_input=raw_user_input,
        onboarding_payload=onboarding_payload,
        allow_search=allow_search,
        state_before=state_before,
        manager_decision=manager_decision,
        onboarding_result=onboarding_result,
        nutrition_artifact=nutrition_artifact,
        persistence_result=persistence_result,
        remaining_budget=remaining_budget,
        state_after=state_after,
        assistant_message=assistant_message,
        sidecar=sidecar,
        state_delta=state_mutation_summary,
        latency_tracking=latency_tracking,
    )
    trace_refs = build_trace_refs(request_id=request_id)

    return {
        "request_id": request_id,
        "assistant_message": assistant_message,
        "manager_decision": {
            "intent_type": manager_decision.intent_type,
            "workflow_effect": manager_decision.workflow_effect,
            "response_summary": manager_decision.response_summary,
            "pending_followup": manager_decision.pending_followup,
            "tool_calls": list(manager_decision.tool_calls),
            "llm_used": manager_decision.llm_used,
            "trace": manager_decision.trace,
        },
        "bundle2_manager": {
            "decision_1": None,
            "decision_2": None,
        },
        "remaining_budget": {
            "status": remaining_budget.status,
            "daily_target_kcal": remaining_budget.daily_target_kcal,
            "consumed_kcal": remaining_budget.consumed_kcal,
            "remaining_kcal": remaining_budget.remaining_kcal,
            "meal_count": remaining_budget.meal_count,
        },
        "sidecar": sidecar,
        "state_delta": state_mutation_summary,
        "audit": trace_refs,
        "hard_fail_conditions": [],
        "shadow_mode": True,
        "latency_tracking": latency_tracking,
    }
