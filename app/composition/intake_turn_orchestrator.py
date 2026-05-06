from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4
from sqlalchemy.orm import Session

from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.composition.intake_execution_orchestrator import process_intake_execution_turn
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.composition.manual_daily_target_chat import (
    apply_manual_daily_target_from_chat,
    manual_daily_target_trace_payload,
)
from app.composition.non_fooddb_read_only_turn import (
    build_non_fooddb_read_tool_executor,
    finalize_non_fooddb_read_only_manager_intent,
)
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.composition.state_resolver import resolve_intake_state
from app.database import get_or_create_user
from app.intake.application.intake_trace_tools import append_trace_event_tool
from app.intake.application.intake_turn_support import (
    intake_turn_latency_tracking,
    intake_turn_manager_decision_payload,
    intake_turn_trace_summary,
    initial_intake_turn_state_mutation_summary,
    normalized_activity_level,
    resolve_local_date,
)
from app.intake.application.phase_a_runtime_context import prepare_phase_a_runtime_context
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.runtime.agent.manager import IntakeManagerResult
from app.runtime.application.execution_guard import validate_onboarding_seed
from app.runtime.application.manager_service import run_intake_manager
from app.runtime.application.reply_renderer import render_intake_reply
from app.runtime.application.request_trace_artifacts import build_trace_refs, write_intake_turn_trace_artifact
from app.runtime.application.sidecar_service import build_deterministic_sidecar
from app.runtime.contracts.phase_a import CurrentTurnContextV1, HistoryExpansionPolicy, ManagerContextPack


@dataclass(frozen=True)
class IntakeOnboardingPayload:
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


async def execute_intake_turn(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str | None,
    onboarding_payload: IntakeOnboardingPayload | None,
    local_date: str | None,
    allow_search: bool,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_port: WebSearchPort | None = None,
    extract_port: WebExtractPort | None = None,
    state_before: Any | None = None,
    current_turn_context: CurrentTurnContextV1 | None = None,
    manager_context_pack: ManagerContextPack | None = None,
    manager_context_packet_v1: dict[str, Any] | None = None,
    phase_a_trace: dict[str, Any] | None = None,
    _timing_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_id = uuid4().hex
    stage_timings: list[dict[str, Any]] = []
    resolved_local_date = resolve_local_date(local_date)
    active_manager_provider = manager_provider or provider

    if state_before is None:
        stage_start = int(time.time() * 1000)
        state_before = resolve_intake_state(
            db,
            user_external_id=user_external_id,
            local_date=resolved_local_date,
            incoming_user_text=raw_user_input,
        )
        _record_timing(stage_timings, "state_resolution", int(time.time() * 1000) - stage_start)
    else:
        _record_timing(stage_timings, "state_resolution", 0)

    phase_a_runtime = prepare_phase_a_runtime_context(
        raw_user_input=raw_user_input,
        resolved_state=state_before,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        phase_a_trace=phase_a_trace,
    )
    current_turn_context = phase_a_runtime.current_turn_context
    manager_context_pack = phase_a_runtime.manager_context_pack
    phase_a_trace = phase_a_runtime.phase_a_trace
    shadow_runtime = phase_a_runtime.shadow_runtime
    if manager_context_packet_v1 is None:
        manager_context_packet_v1 = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=current_turn_context,
            user_external_id=user_external_id,
            local_date=resolved_local_date,
            session_id=request_id,
        )

    stage_start = int(time.time() * 1000)
    manager_decision: IntakeManagerResult = await run_intake_manager(
        provider=active_manager_provider,
        raw_user_input=raw_user_input or "",
        onboarding_payload=onboarding_payload.__dict__ if onboarding_payload is not None else None,
        resolved_state=state_before,
        available_tools=("answer_usage_question", "read_body_plan", "read_day_budget"),
        tool_executor=build_non_fooddb_read_tool_executor(
            db,
            user_id=state_before.user_id,
            local_date=resolved_local_date,
        ),
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        manager_context_packet_v1=manager_context_packet_v1,
        history_expansion_policy=HistoryExpansionPolicy(),
        phase_a_shadow_hypothesis=shadow_runtime.manager_payload if shadow_runtime is not None else None,
    )
    manager_decision_ms = int(time.time() * 1000) - stage_start
    _record_timing(stage_timings, "manager_decision", manager_decision_ms)
    append_trace_event_tool(
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
    assistant_message_override = None
    state_mutation_summary = initial_intake_turn_state_mutation_summary()
    read_only_result = finalize_non_fooddb_read_only_manager_intent(
        db=db,
        manager_decision=manager_decision,
        user_id=state_before.user_id,
        local_date=resolved_local_date,
        request_id=request_id,
        build_remaining_budget=build_remaining_budget_answer_contract,
        append_trace_event=append_trace_event_tool,
    )
    if read_only_result is not None:
        remaining_budget = read_only_result["remaining_budget"]
        assistant_message_override = read_only_result["assistant_message_override"]
    if manager_decision.intent_type == "complete_onboarding":
        if onboarding_payload is None:
            raise ValueError("Structured onboarding payload is required for complete_onboarding.")
        user = get_or_create_user(db, user_external_id)
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
            raise ValueError(f"Intake onboarding guard failed: {', '.join(guard.violations)}")
        state_mutation_summary["body_plan_seeded"] = True
        append_trace_event_tool(
            request_id=request_id,
            stage="v2_onboarding_seed",
            status="ok",
            summary={
                "daily_budget_kcal": onboarding_result.target_result.recommended_target_kcal,
                "estimated_tdee_kcal": onboarding_result.target_result.estimated_tdee_kcal,
                "safety_floor_kcal": onboarding_result.target_result.safety_floor_kcal,
            },
        )
    elif read_only_result is not None:
        pass
    elif manager_decision.intent_type == "set_manual_daily_target":
        user = get_or_create_user(db, user_external_id)
        try:
            manual_target_result = apply_manual_daily_target_from_chat(
                db,
                user=user,
                manager_decision=manager_decision,
                local_date=resolved_local_date,
            )
        except ValueError as exc:
            persistence_result = {
                "manual_daily_target": {
                    "status": "blocked",
                    "reason": str(exc),
                    "source": "manager_structured_decision",
                }
            }
            state_mutation_summary["manual_daily_target_blocked"] = True
            assistant_message_override = (
                "I need an explicit daily target between 800 and 5000 kcal before updating it."
            )
            append_trace_event_tool(
                request_id=request_id,
                stage="v2_manual_daily_target_update",
                status="blocked",
                summary={"reason": str(exc), "source": "manager_structured_decision"},
            )
        else:
            persistence_result = manual_daily_target_trace_payload(manual_target_result)
            state_mutation_summary["manual_daily_target_updated"] = True
            state_mutation_summary["manual_daily_target_kcal"] = manual_target_result.current_budget_view.budget_kcal
            state_mutation_summary["body_plan_seeded"] = bool(manual_target_result.previous_daily_target_kcal is None)
            append_trace_event_tool(
                request_id=request_id,
                stage="v2_manual_daily_target_update",
                status="ok",
                summary={
                    "daily_target_kcal": manual_target_result.current_budget_view.budget_kcal,
                    "previous_daily_target_kcal": manual_target_result.previous_daily_target_kcal,
                    "source": "manager_structured_decision",
                    "live_llm_invoked": manual_target_result.live_llm_invoked,
                },
            )
    elif manager_decision.intent_type == "manager_unavailable":
        append_trace_event_tool(
            request_id=request_id,
            stage="v2_manager_unavailable",
            status="safe_failure",
            summary={
                "reason": "manager_provider_unavailable",
                "state_mutation": "none",
            },
        )
    elif manager_decision.intent_type == "log_meal":
        if not raw_user_input or not raw_user_input.strip():
            raise ValueError("raw_user_input is required for intake logging.")
        return await process_intake_execution_turn(
            db=db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=resolved_local_date,
            allow_search=allow_search,
            manager_provider=manager_provider,
            provider=provider,
            search_port=search_port,
            extract_port=extract_port,
            state_before=state_before,
            manager_decision=manager_decision,
            request_id=request_id,
            stage_timings=stage_timings,
            current_turn_context=current_turn_context,
            manager_context_pack=manager_context_pack,
            manager_context_packet_v1=manager_context_packet_v1,
            phase_a_trace=phase_a_trace,
        )
    else:
        raise ValueError(f"Unsupported intake intent_type: {manager_decision.intent_type}")

    state_after = resolve_intake_state(
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

    assistant_message = assistant_message_override or render_intake_reply(
        intent_type=manager_decision.intent_type,
        onboarding_result=onboarding_result,
        remaining_budget=remaining_budget,
        active_body_plan_view=state_after.active_body_plan_view,
        nutrition_payload=None,
        persistence_result=persistence_result,
        manager_final_action=None,
        budget_summary=None,
    )
    trace_summary = intake_turn_trace_summary(request_id=request_id, manager_decision=manager_decision)
    sidecar = build_deterministic_sidecar(
        active_body_plan_view=state_after.active_body_plan_view,
        current_budget_view=state_after.current_budget_view,
        state_mutation_summary=state_mutation_summary,
        trace_summary=trace_summary,
        overshoot_summary=None,
    )
    append_trace_event_tool(
        request_id=request_id,
        stage="v2_renderer_sidecar",
        status="ok",
        summary={
            "assistant_message": assistant_message,
            "state_delta": state_mutation_summary,
        },
    )

    latency_tracking = intake_turn_latency_tracking(manager_decision=manager_decision, stage_timings=stage_timings)

    write_intake_turn_trace_artifact(
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
        phase_a_trace=phase_a_trace,
        latency_tracking=latency_tracking,
    )
    trace_refs = build_trace_refs(request_id=request_id)

    return {
        "request_id": request_id,
        "assistant_message": assistant_message,
        "manager_decision": intake_turn_manager_decision_payload(manager_decision),
        "intake_execution_manager": {
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
