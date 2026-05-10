from __future__ import annotations

from typing import Any

_CATEGORIES = (
    "db_state",
    "manager_provider",
    "manager_tool_execution",
    "manager_guard",
    "manager_orchestration",
    "persistence",
    "renderer",
    "other",
)

_STAGE_CATEGORY = {
    "state_resolution": "db_state",
    "state_after_resolution": "db_state",
    "tool_batch": "manager_tool_execution",
    "tool_persist_meal_log": "persistence",
    "manager_transition_guard": "manager_guard",
    "renderer_response": "renderer",
}

_REACT_TRACE_REPLACED_STAGES = {"manager_loop"}
_REACT_TRACE_NESTED_STAGES = {
    "phase_a_history_expansion",
    "tool_batch",
    "manager_transition_guard",
}


def _duration_ms(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _stage_name(stage: dict[str, Any]) -> str:
    return str(stage.get("stage") or "").strip()


def _react_trace_totals(react_trace: dict[str, Any] | None) -> dict[str, int]:
    trace = dict(react_trace or {})
    manager_round_latency = trace.get("manager_round_latency_ms")
    if isinstance(manager_round_latency, list):
        manager_provider = sum(_duration_ms(item) for item in manager_round_latency)
    else:
        manager_provider = 0
    return {
        "manager_provider": manager_provider,
        "manager_tool_execution": _duration_ms(trace.get("tool_batch_latency_ms")),
        "manager_guard": _duration_ms(trace.get("guard_latency_ms")),
        "manager_orchestration": _duration_ms(trace.get("orchestration_latency_ms")),
    }


def _react_trace_total_ms(react_trace: dict[str, Any] | None, react_totals: dict[str, int]) -> int:
    trace = dict(react_trace or {})
    return _duration_ms(trace.get("total_latency_ms")) or sum(react_totals.values())


def _has_react_trace_time(react_totals: dict[str, int]) -> bool:
    return any(_duration_ms(value) > 0 for value in react_totals.values())


def _is_react_trace_nested_stage(stage_name: str) -> bool:
    return stage_name in _REACT_TRACE_NESTED_STAGES or stage_name.startswith("manager_pass")


def build_latency_attribution(
    *,
    stage_timings: list[dict[str, Any]],
    react_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attribute current-turn latency without treating attribution as product truth."""

    category_totals = {category: 0 for category in _CATEGORIES}
    raw_stage_duration_ms = sum(_duration_ms(stage.get("duration_ms")) for stage in stage_timings)
    react_totals = _react_trace_totals(react_trace)
    react_trace_present = _has_react_trace_time(react_totals)
    observed_stage_duration_ms = 0
    replaced_manager_loop_stage_ms = 0
    excluded_nested_stage_ms = 0

    for stage in stage_timings:
        name = _stage_name(stage)
        duration_ms = _duration_ms(stage.get("duration_ms"))
        if react_trace_present and name in _REACT_TRACE_REPLACED_STAGES:
            replaced_manager_loop_stage_ms += duration_ms
            continue
        if react_trace_present and _is_react_trace_nested_stage(name):
            excluded_nested_stage_ms += duration_ms
            continue
        category = _STAGE_CATEGORY.get(name)
        if category is None:
            category = "manager_provider" if name.startswith("manager_pass") else "other"
        category_totals[category] += duration_ms
        observed_stage_duration_ms += duration_ms

    total_observed_ms = observed_stage_duration_ms
    if react_trace_present:
        for category, duration_ms in react_totals.items():
            category_totals[category] += duration_ms
        total_observed_ms += _react_trace_total_ms(react_trace, react_totals)

    total_attributed_ms = sum(category_totals.values())
    return {
        "schema_version": "current_shell_latency_attribution.v1",
        "trace_only": True,
        "raw_stage_duration_ms": raw_stage_duration_ms,
        "replaced_manager_loop_stage_ms": replaced_manager_loop_stage_ms,
        "excluded_nested_stage_ms": excluded_nested_stage_ms,
        "total_observed_ms": total_observed_ms,
        "total_attributed_ms": min(total_observed_ms, total_attributed_ms),
        "unattributed_ms": max(0, total_observed_ms - total_attributed_ms),
        "category_totals_ms": category_totals,
        "stage_count": len(stage_timings),
        "sources": {
            "manager_loop": "react_trace" if react_trace_present else "stage_timings",
            "db_renderer_persistence": "stage_timings",
        },
        "non_claims": {
            "product_readiness_claimed": False,
            "latency_slo_pass_claimed": False,
            "provider_latency_truth_invented": False,
        },
    }
