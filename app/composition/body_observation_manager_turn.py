from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.composition.body_observation_manager_tool_runtime import (
    body_observation_guard,
    build_body_observation_tool_executor,
)
from app.composition.state_resolver import resolve_intake_state
from app.intake.application.intake_trace_tools import append_trace_event_tool
from app.intake.application.intake_turn_support import (
    initial_intake_turn_state_mutation_summary,
    intake_turn_latency_tracking,
    intake_turn_manager_decision_payload,
    intake_turn_trace_summary,
)
from app.runtime.application.manager_service import run_intake_manager
from app.runtime.application.request_trace_artifacts import (
    build_trace_refs,
    write_intake_turn_trace_artifact,
)
from app.runtime.application.sidecar_service import build_deterministic_sidecar
from app.runtime.contracts.phase_a import (
    CurrentTurnContextV1,
    HistoryExpansionPolicy,
    ManagerContextPack,
)

BODY_OBSERVATION_MANAGER_TOOLS = ("body.record_observation",)

async def execute_body_observation_manager_turn(
    db: Session,
    *,
    request_id: str,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    allow_search: bool,
    manager_provider: Any,
    state_before: Any,
    current_turn_context: CurrentTurnContextV1 | None,
    manager_context_pack: ManagerContextPack | None = None,
    manager_context_packet_v1: dict[str, Any] | None = None,
    phase_a_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_timings: list[dict[str, Any]] = []
    stage_start = int(time.time() * 1000)
    manager_decision = await run_intake_manager(
        provider=manager_provider,
        raw_user_input=raw_user_input,
        resolved_state=state_before,
        available_tools=BODY_OBSERVATION_MANAGER_TOOLS,
        tool_executor=build_body_observation_tool_executor(
            db,
            user_external_id=user_external_id,
            local_date=local_date,
        ),
        guard_checker=body_observation_guard,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        manager_context_packet_v1=manager_context_packet_v1,
        history_expansion_policy=HistoryExpansionPolicy(),
    )
    stage_timings.append(
        {
            "stage": "body_observation_manager_decision",
            "duration_ms": int(time.time() * 1000) - stage_start,
        }
    )
    append_trace_event_tool(
        request_id=request_id,
        stage="v2_body_observation_manager_decision",
        status="ok",
        summary={
            "intent_type": manager_decision.intent_type,
            "workflow_effect": manager_decision.workflow_effect,
            "tool_calls": list(manager_decision.tool_calls),
            "tool_result_count": len(manager_decision.tool_results),
            "llm_used": manager_decision.llm_used,
        },
    )

    state_mutation_summary = initial_intake_turn_state_mutation_summary()
    recorded_tool_result = next(
        (
            item
            for item in manager_decision.tool_results
            if isinstance(item, dict)
            and str(
                (
                    item.get("provenance")
                    if isinstance(item.get("provenance"), dict)
                    else {}
                ).get("canonical_tool_name")
                or item.get("tool_name")
                or ""
            )
            == "body.record_observation"
            and bool(
                (
                    item.get("mutation_result")
                    if isinstance(item.get("mutation_result"), dict)
                    else {}
                ).get("body_observation_recorded")
            )
        ),
        None,
    )
    state_mutation_summary["body_observation_recorded"] = recorded_tool_result is not None

    state_after = resolve_intake_state(
        db,
        user_external_id=user_external_id,
        local_date=local_date,
    )
    assistant_message = str(
        manager_decision.answer_contract.get("reply_text")
        or manager_decision.response_summary
        or (
            "Recorded weight observation without changing body plan."
            if recorded_tool_result is not None
            else "I could not safely record that body observation."
        )
    )
    trace_summary = intake_turn_trace_summary(
        request_id=request_id,
        manager_decision=manager_decision,
    )
    sidecar = build_deterministic_sidecar(
        active_body_plan_view=state_after.active_body_plan_view,
        current_budget_view=state_after.current_budget_view,
        state_mutation_summary=state_mutation_summary,
        trace_summary=trace_summary,
        overshoot_summary=None,
    )
    latency_tracking = intake_turn_latency_tracking(
        manager_decision=manager_decision,
        stage_timings=stage_timings,
    )

    write_intake_turn_trace_artifact(
        request_id=request_id,
        user_external_id=user_external_id,
        local_date=local_date,
        raw_user_input=raw_user_input,
        onboarding_payload=None,
        allow_search=allow_search,
        state_before=state_before,
        manager_decision=manager_decision,
        onboarding_result=None,
        nutrition_artifact=None,
        persistence_result=recorded_tool_result,
        remaining_budget=None,
        state_after=state_after,
        assistant_message=assistant_message,
        sidecar=sidecar,
        state_delta=state_mutation_summary,
        phase_a_trace=phase_a_trace,
        latency_tracking=latency_tracking,
    )

    return {
        "request_id": request_id,
        "assistant_message": assistant_message,
        "manager_decision": intake_turn_manager_decision_payload(manager_decision),
        "intake_execution_manager": {
            "final": {
                "final_action": manager_decision.final_action,
                "workflow_effect": manager_decision.workflow_effect,
            },
            "persistence_result": recorded_tool_result,
        },
        "sidecar": sidecar,
        "state_delta": state_mutation_summary,
        "audit": build_trace_refs(request_id=request_id),
        "hard_fail_conditions": [],
        "shadow_mode": True,
        "latency_tracking": latency_tracking,
    }


__all__ = [
    "BODY_OBSERVATION_MANAGER_TOOLS",
    "execute_body_observation_manager_turn",
]
