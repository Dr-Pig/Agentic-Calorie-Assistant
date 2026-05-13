from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.advanced_shadow_lab.context_engineering_holdout_gate import (
    build_context_engineering_holdout_gate,
    holdout_case_blockers,
)


def test_context_engineering_holdout_gate_covers_negative_cases_without_overtrigger() -> None:
    gate = build_context_engineering_holdout_gate()

    assert gate["artifact_type"] == "advanced_product_lab_ce_stress_holdout_report"
    assert gate["status"] == "pass"
    assert gate["negative_holdout_case_count"] == 8
    assert gate["overtrigger_violation_count"] == 0
    assert gate["undertrigger_violation_count"] == 0
    assert gate["prompt_injection_case_ids"] == ["ce-stress-027"]
    assert gate["mainline_activation_enabled"] is False
    assert gate["canonical_product_mutation_allowed"] is False
    assert gate["scheduler_delivery_allowed"] is False
    assert gate["raw_user_text_semantic_inference_performed"] is False
    assert gate["blockers"] == []


def test_holdout_case_blockers_detect_forbidden_and_missing_capabilities() -> None:
    case = next(
        item
        for item in load_context_engineering_golden_set()["cases"]
        if item["case_id"] == "ce-stress-023"
    )

    assert holdout_case_blockers(case, ["rescue"]) == [
        "ce-stress-023.required_capability.missing:query",
        "ce-stress-023.forbidden_capability.invoked:rescue",
    ]


def test_context_engineering_holdout_gate_keeps_no_op_cases_no_op() -> None:
    gate = build_context_engineering_holdout_gate()
    by_id = {case["case_id"]: case for case in gate["cases"]}

    assert by_id["ce-stress-024"]["invoked_capabilities"] == []
    assert by_id["ce-stress-027"]["invoked_capabilities"] == []
    assert by_id["ce-stress-029"]["invoked_capabilities"] == []
    assert by_id["ce-stress-024"]["no_op_answer"] is True
