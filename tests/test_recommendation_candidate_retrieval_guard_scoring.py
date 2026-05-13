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


def test_candidate_retrieval_guard_scoring_declares_deterministic_boundary() -> None:
    artifact = build_candidate_retrieval_guard_scoring(
        planning=_planning(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t2",
        ),
    )

    assert artifact["node"] == "candidate_retrieval_guard_scoring"
    assert artifact["owner"] == "deterministic"
    assert artifact["llm_semantic_authority"] is False
    assert artifact["candidate_source_port_used"] is True
    assert artifact["candidate_source_port_status"] == "pass"
    assert artifact["hard_blocker_families"] == [
        "premeal_constraint",
        "budget",
        "negative_preference",
        "rescue_conflict",
        "availability",
        "memory_action",
    ]
    assert artifact["may_mutate_canonical_state"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["blockers"] == []


def test_candidate_retrieval_guard_scoring_emits_quality_and_omission_trace() -> None:
    artifact = build_candidate_retrieval_guard_scoring(
        planning=_planning(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t2",
        ),
    )

    filtered = {
        item["candidate_id"]: item["reason_codes"]
        for item in artifact["filtered_candidates"]
    }
    assert filtered["over-1"] == ["over_budget"]
    assert filtered["cilantro-1"] == ["confirmed_negative_preference"]
    assert filtered["fried-1"] == ["accepted_rescue_conflict"]
    assert filtered["closed-1"] == ["unavailable"]
    assert artifact["scoring_trace"][0]["source_node"] == (
        "candidate_retrieval_guard_scoring"
    )
    assert artifact["scoring_trace"][0]["score_owner"] == "deterministic"
    assert artifact["quality_signals"][0]["candidate_id"] in artifact[
        "qualified_candidate_ids"
    ]


def test_recommendation_train_records_pr7_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 17
    assert plan["last_completed_pr_number"] >= 7
    assert plan["active_pr_number"] >= 8
    assert {
        "pr_number": 7,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_candidate_retrieval_guard_scoring_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _planning() -> dict[str, object]:
    return {
        "candidate_spec": {
            "budget_posture": {"remaining_kcal": 700, "max_candidate_kcal": 700},
            "pre_meal_planning": {},
            "swap_suggestion": {},
        }
    }
