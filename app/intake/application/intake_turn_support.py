from __future__ import annotations

from datetime import datetime
from typing import Any


def normalized_activity_level(activity_level: str | None) -> str:
    value = (activity_level or "").strip().lower()
    return value or "sedentary"


def resolve_local_date(local_date: str | None) -> str:
    if isinstance(local_date, str) and local_date.strip():
        return local_date.strip()
    return datetime.now().date().isoformat()


def initial_intake_turn_state_mutation_summary() -> dict[str, Any]:
    return {
        "body_plan_seeded": False,
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
    }


def intake_turn_latency_tracking(
    *,
    manager_decision: Any,
    stage_timings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
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


def intake_turn_trace_summary(*, request_id: str, manager_decision: Any) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "manager_intent": manager_decision.intent_type,
        "tool_calls": list(manager_decision.tool_calls),
        "llm_used": manager_decision.llm_used,
    }


def intake_turn_manager_decision_payload(manager_decision: Any) -> dict[str, Any]:
    return {
        "intent_type": manager_decision.intent_type,
        "workflow_effect": manager_decision.workflow_effect,
        "response_summary": manager_decision.response_summary,
        "pending_followup": manager_decision.pending_followup,
        "semantic_decision": dict(getattr(manager_decision, "semantic_decision", {}) or {}),
        "tool_calls": list(manager_decision.tool_calls),
        "llm_used": manager_decision.llm_used,
        "trace": manager_decision.trace,
    }


def payload_trace_contract(payload: Any) -> dict[str, Any]:
    trace_contract = getattr(payload, "trace_contract", None) or {}
    return dict(trace_contract)


def payload_unresolved_info(payload: Any) -> list[str]:
    trace_contract = payload_trace_contract(payload)
    raw = trace_contract.get("unresolved_info") or []
    return [str(item) for item in raw if str(item).strip()]
