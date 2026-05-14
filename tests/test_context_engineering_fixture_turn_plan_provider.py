from __future__ import annotations

import json

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.advanced_shadow_lab.context_engineering_fixture_turn_plan_provider import (
    FixtureContextEngineeringTurnPlanProvider,
    build_context_engineering_fixture_turn_plan_trace,
    fixture_turn_plan_output_blockers,
)


def _case(case_id: str) -> dict[str, object]:
    return next(
        case
        for case in load_context_engineering_golden_set()["cases"]
        if case["case_id"] == case_id
    )


def test_fixture_turn_plan_provider_emits_structured_plan_without_keyword_route() -> None:
    provider = FixtureContextEngineeringTurnPlanProvider(model_profile="fixture-fast")
    case = _case("ce-stress-001")

    artifact = provider.plan_case(case)
    serialized = json.dumps(artifact)

    assert artifact["artifact_type"] == "advanced_product_lab_fixture_turn_plan_trace"
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fixture_provider_contract"
    assert artifact["owner"] == "manager_llm_fixture_provider"
    assert artifact["model_profile"] == "fixture-fast"
    assert artifact["raw_user_text_semantic_inference_performed"] is False
    assert artifact["case_user_turn_included"] is False
    assert str(case["user_turn"]) not in serialized
    assert "keyword_route" not in serialized
    assert artifact["manager_turn_plan_grade"]["status"] == "pass"
    assert artifact["tool_choice_validation"]["status"] == "pass"

    plan = artifact["manager_turn_plan"]
    assert [item["capability"] for item in plan["capability_requests"]] == [
        "intake",
        "query",
        "rescue",
        "recommendation",
    ]
    assert plan["capability_requests"][0]["arguments"]["intake_manager_result"][
        "artifact_type"
    ] == "advanced_lab_intake_manager_result_contract_stub"


def test_fixture_turn_plan_trace_covers_selected_ce_stress_cases() -> None:
    trace = build_context_engineering_fixture_turn_plan_trace(
        case_ids=["ce-stress-001", "ce-stress-006", "ce-stress-007", "ce-stress-012"]
    )

    assert trace["artifact_type"] == "advanced_product_lab_fixture_turn_plan_suite_trace"
    assert trace["status"] == "pass"
    assert trace["case_count"] == 4
    assert trace["mainline_activation_enabled"] is False
    assert trace["canonical_product_mutation_allowed"] is False
    assert trace["raw_user_text_semantic_inference_performed"] is False
    assert trace["blockers"] == []


def test_fixture_turn_plan_output_blocks_forbidden_fields_and_mutation_flags() -> None:
    blockers = fixture_turn_plan_output_blockers(
        {
            "artifact_type": "advanced_product_lab_fixture_turn_plan_trace",
            "raw_user_text": "do not route this",
            "keyword_route": "ramen means recommendation",
            "manager_turn_plan": {"canonical_product_mutation_allowed": True},
        }
    )

    assert blockers == [
        "turn_plan_output.forbidden_field:keyword_route",
        "turn_plan_output.forbidden_field:raw_user_text",
        "manager_turn_plan.canonical_product_mutation_allowed_true",
    ]
