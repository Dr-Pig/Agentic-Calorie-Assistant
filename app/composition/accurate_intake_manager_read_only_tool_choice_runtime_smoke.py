from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_manager_read_only_tool_choice_runtime_support import (
    REQUIRED_CASE_IDS,
    RuntimeCase,
    bootstrap_runtime_state,
    build_fixture_manager_decision,
    build_runtime_session,
    runtime_cases,
)
from app.composition.non_fooddb_read_only_turn import (
    finalize_non_fooddb_read_only_manager_intent,
)
from app.composition.non_fooddb_read_tool_executor import (
    execute_non_fooddb_read_tool_calls,
)
from app.composition.intake_read_tools import (
    read_body_plan_tool,
    read_calibration_pending_proposal_tool,
    read_day_budget_tool,
    read_latest_weight_observation_tool,
)

def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _normalize_finalizer_output(value: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(value or {})
    remaining_budget = payload.get("remaining_budget")
    if remaining_budget is not None and not isinstance(remaining_budget, dict):
        if is_dataclass(remaining_budget):
            payload["remaining_budget"] = asdict(remaining_budget)
        elif hasattr(remaining_budget, "model_dump"):
            try:
                payload["remaining_budget"] = remaining_budget.model_dump(mode="json")
            except TypeError:
                payload["remaining_budget"] = remaining_budget.model_dump()
        else:
            payload["remaining_budget"] = _json_safe(remaining_budget)
    return _json_safe(payload)


def _state_fingerprint(*, db: Any, user_id: int, local_date: str) -> dict[str, Any]:
    budget_view = read_day_budget_tool(db, user_id=user_id, local_date=local_date)
    active_plan = read_body_plan_tool(db, user_id=user_id)
    latest_weight = read_latest_weight_observation_tool(db, user_id=user_id, local_date=local_date)
    proposals = read_calibration_pending_proposal_tool(db, user_id=user_id)
    return _json_safe(
        {
            "budget": {
                "budget_kcal": getattr(budget_view, "budget_kcal", None),
                "consumed_kcal": getattr(budget_view, "consumed_kcal", None),
                "remaining_kcal": getattr(budget_view, "remaining_kcal", None),
                "active_meal_count": getattr(budget_view, "active_meal_count", None),
            },
            "active_plan": {
                "body_plan_id": getattr(active_plan, "body_plan_id", None),
                "goal_type": getattr(active_plan, "goal_type", None),
                "daily_budget_kcal": getattr(active_plan, "daily_budget_kcal", None),
            },
            "latest_weight": None
            if latest_weight is None
            else {
                "observation_id": getattr(latest_weight, "observation_id", None),
                "value": getattr(latest_weight, "value", None),
                "unit": getattr(latest_weight, "unit", None),
                "local_date": getattr(latest_weight, "local_date", None),
            },
            "pending_proposal_count": len(proposals),
        }
    )


async def _execute_case(case: RuntimeCase) -> dict[str, Any]:
    db = build_runtime_session()
    user = bootstrap_runtime_state(
        db,
        user_external_id=f"runtime-smoke-{case.case_id}",
        latest_weight_required=case.latest_weight_required,
    )
    state_before = _state_fingerprint(db=db, user_id=user.id, local_date="2026-05-06")
    tool_results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[{"name": case.selected_tool}],
    )
    trace_events: list[dict[str, Any]] = []
    finalizer_output = finalize_non_fooddb_read_only_manager_intent(
        db=db,
        manager_decision=build_fixture_manager_decision(case, _json_safe(tool_results)),
        user_id=user.id,
        local_date="2026-05-06",
        request_id=f"req-{case.case_id}",
        append_trace_event=lambda **kwargs: trace_events.append(_json_safe(kwargs)),
    )
    state_after = _state_fingerprint(db=db, user_id=user.id, local_date="2026-05-06")
    db.close()
    first_result = tool_results[0] if tool_results else {}
    finalizer_mode = "none"
    if isinstance(finalizer_output, dict):
        if finalizer_output.get("remaining_budget") is not None:
            finalizer_mode = "remaining_budget"
        elif finalizer_output.get("assistant_message_override") is not None:
            finalizer_mode = "assistant_message_override"
    return _json_safe(
        {
            "case_id": case.case_id,
            "selected_tool": case.selected_tool,
            "tool_results": tool_results,
            "trace_events": trace_events,
            "finalizer_output": _normalize_finalizer_output(finalizer_output),
            "finalizer_mode": finalizer_mode,
            "response_summary": case.workflow_effect,
            "tool_result_summary": {
                "tool_name": first_result.get("tool_name"),
                "canonical_tool_name": (first_result.get("provenance") or {}).get("canonical_tool_name"),
                "truth_owner": (first_result.get("provenance") or {}).get("truth_owner"),
                "mutation_authority": (first_result.get("provenance") or {}).get("mutation_authority"),
                "tool_kind": (first_result.get("provenance") or {}).get("tool_kind"),
                "failure_family": first_result.get("failure_family"),
            },
            "state_mutation": {
                "observed_no_mutation": state_before == state_after,
                "before": state_before,
                "after": state_after,
            },
        }
    )


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = {str(case.get("case_id")) for case in cases}
    for case_id in REQUIRED_CASE_IDS:
        if case_id not in case_ids:
            blockers.append(f"missing_case:{case_id}")
    for case in cases:
        case_id = str(case.get("case_id"))
        selected_tool = str(case.get("selected_tool") or "")
        summary = case.get("tool_result_summary") if isinstance(case.get("tool_result_summary"), dict) else {}
        finalizer_output = case.get("finalizer_output") if isinstance(case.get("finalizer_output"), dict) else {}
        state_mutation = case.get("state_mutation") if isinstance(case.get("state_mutation"), dict) else {}
        if summary.get("tool_name") != selected_tool:
            blockers.append(f"{case_id}.tool_name_selected_tool_mismatch")
        if summary.get("canonical_tool_name") != selected_tool:
            blockers.append(f"{case_id}.canonical_tool_name_selected_tool_mismatch")
        if summary.get("mutation_authority") is not False:
            blockers.append(f"{case_id}.mutation_authority")
        if summary.get("tool_kind") != "read_only":
            blockers.append(f"{case_id}.tool_kind_not_read_only")
        if summary.get("failure_family") is not None:
            blockers.append(f"{case_id}.tool_execution_failed")
        if state_mutation.get("observed_no_mutation") is not True:
            blockers.append(f"{case_id}.observed_no_mutation_failed")
        if case_id == "budget_remaining_runtime_read":
            remaining_budget = finalizer_output.get("remaining_budget")
            if not isinstance(remaining_budget, dict):
                blockers.append(f"{case_id}.remaining_budget_missing")
            elif remaining_budget.get("remaining_kcal") is None:
                blockers.append(f"{case_id}.remaining_kcal_missing")
        else:
            if finalizer_output.get("assistant_message_override") is None:
                blockers.append(f"{case_id}.assistant_message_override_missing")
    return blockers


async def build_manager_read_only_tool_choice_runtime_smoke_artifact() -> dict[str, Any]:
    cases = [_json_safe(await _execute_case(case)) for case in runtime_cases()]
    blockers = _validate(cases)
    artifact = {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_manager_read_only_public_tool_runtime_smoke",
        "status": "manager_read_only_public_tool_runtime_smoke_pass",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "current_shell_non_fooddb_read_only_public_tool_runtime_smoke",
        "backing_class": "runtime_backed",
        "semantic_owner": "fixture_manager_structured_decision",
        "tool_execution_owner": "non_fooddb_read_tool_executor",
        "finalizer_owner": "non_fooddb_read_only_turn",
        "required_case_ids": list(REQUIRED_CASE_IDS),
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "runtime_backed_case_count": len(cases),
        },
        "deterministic_selected_tool": False,
        "deterministic_selected_intent": False,
        "manager_context_packet_schema_changed": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "fooddb_used": False,
        "web_tavily_used": False,
        "live_llm_invoked": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "blockers": blockers,
    }
    if blockers:
        artifact["status"] = "blocked"
    return _json_safe(artifact)


__all__ = ["build_manager_read_only_tool_choice_runtime_smoke_artifact"]
