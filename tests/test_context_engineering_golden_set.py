from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_case_loader import (
    GOLDEN_SET_PATH,
    golden_set_case_ids,
    load_context_engineering_golden_set,
)


def test_context_engineering_golden_set_exists_and_loads() -> None:
    artifact = load_context_engineering_golden_set()

    assert GOLDEN_SET_PATH.exists()
    assert artifact["artifact_type"] == "advanced_product_lab_context_engineering_golden_set"
    assert artifact["status"] == "active"
    assert len(artifact["cases"]) == 6


def test_context_engineering_golden_set_schema_covers_overlap_cases() -> None:
    artifact = load_context_engineering_golden_set()

    required = set(artifact["case_schema"]["required_fields"])
    assert {
        "case_id",
        "coverage_scope",
        "user_turn",
        "expected_primary_workflow",
        "expected_capabilities",
        "forbidden_capabilities",
        "expected_ordering_constraints",
        "mutation_posture",
    }.issubset(required)

    case_ids = golden_set_case_ids()
    assert case_ids == ["ce-001", "ce-002", "ce-003", "ce-004", "ce-005", "ce-006"]


def test_context_engineering_golden_set_includes_reusable_meal_and_current_shell_bridge() -> None:
    artifact = load_context_engineering_golden_set()
    by_id = {item["case_id"]: item for item in artifact["cases"]}

    assert by_id["ce-005"]["coverage_scope"] == "current_shell_bridge"
    assert by_id["ce-005"]["expected_capabilities"] == ["query", "memory"]
    assert by_id["ce-006"]["expected_capabilities"] == ["intake", "reusable_meal"]
    assert by_id["ce-006"]["expected_ordering_constraints"] == ["reusable_meal_before_intake"]
