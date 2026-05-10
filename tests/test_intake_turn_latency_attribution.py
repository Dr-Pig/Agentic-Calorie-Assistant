from __future__ import annotations

from types import SimpleNamespace

from app.composition.intake_execution_response import build_latency_tracking
from app.intake.application.intake_turn_support import intake_turn_latency_tracking
from app.intake.application.latency_attribution import build_latency_attribution


def test_latency_attribution_splits_stage_and_react_trace_time_without_double_counting_manager_loop() -> None:
    attribution = build_latency_attribution(
        stage_timings=[
            {"stage": "state_resolution", "duration_ms": 12},
            {"stage": "manager_loop", "duration_ms": 650},
            {"stage": "tool_batch", "duration_ms": 300},
            {"stage": "tool_persist_meal_log", "duration_ms": 40},
            {"stage": "state_after_resolution", "duration_ms": 8},
            {"stage": "renderer_response", "duration_ms": 25},
        ],
        react_trace={
            "manager_round_latency_ms": [100, 200],
            "tool_batch_latency_ms": 300,
            "guard_latency_ms": 40,
            "orchestration_latency_ms": 10,
            "total_latency_ms": 650,
        },
    )

    assert attribution["raw_stage_duration_ms"] == 1035
    assert attribution["replaced_manager_loop_stage_ms"] == 650
    assert attribution["excluded_nested_stage_ms"] == 300
    assert attribution["total_observed_ms"] == 735
    assert attribution["total_attributed_ms"] == 735
    assert attribution["unattributed_ms"] == 0
    assert attribution["category_totals_ms"] == {
        "db_state": 20,
        "manager_provider": 300,
        "manager_tool_execution": 300,
        "manager_guard": 40,
        "manager_orchestration": 10,
        "persistence": 40,
        "renderer": 25,
        "other": 0,
    }
    assert attribution["sources"]["manager_loop"] == "react_trace"
    assert attribution["sources"]["db_renderer_persistence"] == "stage_timings"


def test_latency_tracking_exposes_attribution_for_top_level_and_execution_turns() -> None:
    manager_decision = SimpleNamespace(
        intent_type="log_meal",
        tool_calls=[{"tool_name": "estimate_nutrition"}],
    )
    stage_timings = [
        {"stage": "state_resolution", "duration_ms": 7},
        {"stage": "manager_loop", "duration_ms": 400},
        {"stage": "renderer_response", "duration_ms": 13},
    ]
    react_trace = {
        "manager_round_latency_ms": [120, 140],
        "tool_batch_latency_ms": 100,
        "guard_latency_ms": 20,
        "orchestration_latency_ms": 20,
        "total_latency_ms": 400,
    }

    top_level = intake_turn_latency_tracking(
        manager_decision=manager_decision,
        stage_timings=stage_timings,
        react_trace=react_trace,
    )
    execution = build_latency_tracking(
        manager_decision=manager_decision,
        stage_timings=stage_timings,
        react_trace=react_trace,
    )

    for latency in (top_level, execution):
        assert latency["total_duration_ms"] == 420
        assert latency["latency_attribution"]["category_totals_ms"]["manager_provider"] == 260
        assert latency["latency_attribution"]["category_totals_ms"]["manager_tool_execution"] == 100
        assert latency["latency_attribution"]["category_totals_ms"]["manager_guard"] == 20
        assert latency["latency_attribution"]["category_totals_ms"]["renderer"] == 13
        assert latency["latency_attribution"]["unattributed_ms"] == 0
