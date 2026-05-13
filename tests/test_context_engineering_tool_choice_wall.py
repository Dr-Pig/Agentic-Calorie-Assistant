from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_tool_choice_wall import (
    build_context_engineering_tool_choice_wall_trace,
)


def test_context_engineering_tool_choice_wall_trace_passes_key_overlap_cases() -> None:
    trace = build_context_engineering_tool_choice_wall_trace(
        case_ids=[
            "ce-stress-001",
            "ce-stress-006",
            "ce-stress-007",
            "ce-stress-012",
            "ce-stress-026",
        ]
    )

    assert trace["artifact_type"] == "advanced_product_lab_tool_choice_wall_trace"
    assert trace["status"] == "pass"
    assert trace["lab_enabled"] is True
    assert trace["mainline_activation_enabled"] is False
    assert trace["canonical_mutation_allowed"] is False
    assert trace["durable_product_memory_activation_allowed"] is False
    assert trace["production_scheduler_delivery_allowed"] is False
    assert trace["case_count"] == 5
    assert trace["blockers"] == []


def test_context_engineering_tool_choice_wall_trace_records_pending_intent_tool_order() -> None:
    trace = build_context_engineering_tool_choice_wall_trace(case_ids=["ce-stress-007"])
    case_trace = trace["cases"][0]

    assert case_trace["case_id"] == "ce-stress-007"
    assert case_trace["status"] == "pass"
    assert case_trace["tool_order"] == ["pending_meal_intent.update", "intake.run"]
    assert case_trace["ordering_constraints_checked"] == ["pending_meal_intent_before_intake"]
