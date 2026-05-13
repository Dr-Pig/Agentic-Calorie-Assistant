from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_recommendation_candidates import (
    build_candidate_retrieval_guard_scoring,
)


def test_allowed_pool_trace_exposes_allowed_omitted_and_scoring_reasons() -> None:
    artifact = build_candidate_retrieval_guard_scoring(
        planning=_planning(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t9",
        ),
    )

    trace = artifact["allowed_pool_trace"]
    omitted = {
        item["candidate_id"]: item
        for item in trace["omitted_candidate_trace"]
    }
    scoring = {
        item["candidate_id"]: item
        for item in trace["scoring_reason_trace"]
    }

    assert trace["node"] == "candidate_retrieval_guard_scoring"
    assert trace["owner"] == "deterministic"
    assert trace["llm_semantic_authority"] is False
    assert trace["allowed_candidate_ids"] == artifact["allowed_candidate_ids"]
    assert omitted["over-1"]["reason_codes"] == ["over_budget"]
    assert omitted["cilantro-1"]["reason_codes"] == [
        "confirmed_negative_preference"
    ]
    assert omitted["fried-1"]["reason_codes"] == ["accepted_rescue_conflict"]
    assert omitted["closed-1"]["reason_codes"] == ["unavailable"]
    assert scoring["golden-1"]["quality_score"] > 0
    assert "budget_fit" in scoring["golden-1"]["scoring_reasons"]
    assert scoring["golden-1"]["source_node"] == "candidate_retrieval_guard_scoring"


def test_allowed_pool_trace_is_not_a_new_runtime_or_mutation_surface() -> None:
    artifact = build_candidate_retrieval_guard_scoring(
        planning=_planning(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t9",
        ),
    )

    trace = artifact["allowed_pool_trace"]

    assert trace["runtime_effect_allowed"] is False
    assert trace["recommendation_served"] is False
    assert trace["canonical_product_mutation_allowed"] is False
    assert trace["manager_context_packet_changed"] is False
    assert trace["raw_transcript_included"] is False


def test_recommendation_train_records_pr9_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 15
    assert plan["last_completed_pr_number"] == 9
    assert plan["active_pr_number"] == 10
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 9,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_allowed_pool_trace_completed_locally",
    }


def _planning() -> dict[str, object]:
    return {
        "candidate_spec": {
            "budget_posture": {"remaining_kcal": 700, "max_candidate_kcal": 700},
            "pre_meal_planning": {},
            "swap_suggestion": {},
        }
    }
