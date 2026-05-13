from __future__ import annotations

from app.advanced_shadow_lab.reusable_meal_golden_loader import (
    load_reusable_meal_golden_set,
)
from app.shared.contracts.reusable_meal_policy import evaluate_reusable_meal_policy


def test_reusable_meal_golden_set_has_positive_cases_and_holdouts() -> None:
    artifact = load_reusable_meal_golden_set()

    assert artifact["artifact_type"] == "advanced_product_lab_reusable_meal_golden_set"
    assert artifact["status"] == "active"
    assert len(artifact["cases"]) == 4
    assert len(artifact["holdouts"]) == 2


def test_reusable_meal_golden_set_matches_policy_decisions() -> None:
    artifact = load_reusable_meal_golden_set()
    cases = {case["case_id"]: case for case in artifact["cases"]}

    assert _decision(cases["rm-001"]) == "reuse_exact"
    assert _decision(cases["rm-002"]) == "reuse_anchored"
    assert _decision(cases["rm-003"]) == "re_estimate_required"
    assert _decision(cases["rm-004"]) == "candidate_only"


def test_reusable_meal_holdouts_block_false_matches() -> None:
    artifact = load_reusable_meal_golden_set()
    holdouts = {case["case_id"]: case for case in artifact["holdouts"]}

    assert _decision(holdouts["rm-h001"]) == "re_estimate_required"
    assert _decision(holdouts["rm-h002"]) == "re_estimate_required"


def _decision(case: dict[str, object]) -> str:
    result = evaluate_reusable_meal_policy(
        repetition_count=int(case["repetition_count"]),
        explicit_same_as_before=bool(case["explicit_same_as_before"]),
        ingredient_drift=bool(case["ingredient_drift"]),
        portion_drift=bool(case["portion_drift"]),
        source_drift=bool(case["source_drift"]),
        correction_count=0,
    )
    return str(result["decision"])
