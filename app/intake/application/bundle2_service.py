"""Thin Bundle 2 intake entrypoint.

Semantic ownership lives in the single-manager runtime, domain tools, execution
guard, persistence support, and deterministic sidecar builders.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from ...runtime.application.bundle2_response import build_bundle2_response, finalized_budget_summary
from ...runtime.application.bundle2_tool_batch import apply_final_action_to_payload, execute_manager_tool_calls
from ...runtime.application.manager_service import run_intake_manager
from ...runtime.application.state_resolver import resolve_v2_bundle1_state
from . import manager_tools as tools
from .bundle2_persistence import initial_state_mutation_summary, persist_bundle2_artifact


def _now_ms() -> int:
    return int(time.time() * 1000)


def _append_stage_timing(stage_timings: list[dict[str, Any]], stage: str, duration_ms: int) -> None:
    stage_timings.append({"stage": stage, "duration_ms": duration_ms})


async def process_bundle2_intake(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    allow_search: bool,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_adapter: Any | None = None,
    state_before: Any,
    manager_decision: Any,
    request_id: str,
    stage_timings: list[dict[str, Any]],
) -> dict[str, Any]:
    active_manager_provider = manager_provider or provider
    state_mutation_summary = initial_state_mutation_summary()
    correction_target = tools.resolve_correction_target_tool(resolved_state=state_before)
    tool_state: dict[str, Any] = {
        "correction_target": correction_target,
        "nutrition_artifact": None,
        "budget_summary": None,
    }

    def record_timing(stage: str, duration_ms: int) -> None:
        _append_stage_timing(stage_timings, stage, duration_ms)

    async def tool_executor(**kwargs: Any) -> list[dict[str, Any]]:
        stage_start = _now_ms()
        results = await execute_manager_tool_calls(
            db=db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            request_id=request_id,
            local_date=local_date,
            allow_search=allow_search,
            manager_provider=active_manager_provider,
            provider=provider,
            search_adapter=search_adapter,
            state_before=state_before,
            correction_target=tool_state["correction_target"],
            tool_calls=list(kwargs.get("tool_calls") or []),
            tool_state=tool_state,
        )
        record_timing("tool_batch", _now_ms() - stage_start)
        tools.append_trace_event_tool(
            request_id=request_id,
            stage="v2_tool_batch",
            status="ok",
            summary={"tool_results": results},
        )
        return results

    async def guard_checker(**kwargs: Any) -> dict[str, Any]:
        manager_payload = dict(kwargs.get("manager_payload") or {})
        final_action = str(manager_payload.get("final_action") or "")
        artifact = tool_state.get("nutrition_artifact")
        payload = getattr(artifact, "payload", None) if artifact is not None else None
        if final_action in {"commit", "correction_applied", "overshoot_note"} and payload is None:
            return {
                "ok": False,
                "repair_request": False,
                "failure_family": "commit_without_evidence",
            }
        return {"ok": True}

    stage_start = _now_ms()
    manager_result = await run_intake_manager(
        provider=active_manager_provider,
        raw_user_input=raw_user_input,
        resolved_state=state_before,
        available_tools=("resolve_correction_target", "estimate_nutrition", "compare_against_budget"),
        tool_executor=tool_executor,
        guard_checker=guard_checker,
        constraints={"request_id": request_id},
        max_rounds=3,
    )
    record_timing("manager_loop", _now_ms() - stage_start)
    tools.append_trace_event_tool(
        request_id=request_id,
        stage="v2_manager_loop",
        status="ok",
        summary={
            "manager_rounds": [dict(item) for item in manager_result.manager_rounds],
            "final_action": manager_result.final_action,
            "workflow_effect": manager_result.workflow_effect,
            "request_failure_family": manager_result.request_failure_family,
        },
    )

    nutrition_artifact = tool_state.get("nutrition_artifact")
    budget_summary = tool_state.get("budget_summary")
    payload = getattr(nutrition_artifact, "payload", None) if nutrition_artifact is not None else None
    apply_final_action_to_payload(
        payload=payload,
        raw_user_input=raw_user_input,
        final_action=manager_result.final_action,
    )

    persistence_result = persist_bundle2_artifact(
        db,
        nutrition_artifact=nutrition_artifact,
        final_action=manager_result.final_action,
        request_id=request_id,
        record_timing=record_timing,
        now_ms=_now_ms,
        state_mutation_summary=state_mutation_summary,
    )

    state_after = resolve_v2_bundle1_state(
        db,
        user_external_id=user_external_id,
        local_date=local_date,
    )
    tool_outputs = {"tool_results": [dict(item) for item in manager_result.tool_results]}
    if state_mutation_summary.get("canonical_commit") and budget_summary is not None:
        budget_summary = finalized_budget_summary(
            budget_summary=budget_summary,
            state_before=state_before,
            state_after=state_after,
        )
        tool_outputs["budget_summary"] = budget_summary

    return build_bundle2_response(
        db,
        request_id=request_id,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        allow_search=allow_search,
        state_before=state_before,
        state_after=state_after,
        manager_decision=manager_decision,
        manager_result=manager_result,
        nutrition_artifact=nutrition_artifact,
        persistence_result=persistence_result,
        budget_summary=budget_summary,
        tool_outputs=tool_outputs,
        state_mutation_summary=state_mutation_summary,
        stage_timings=stage_timings,
    )
