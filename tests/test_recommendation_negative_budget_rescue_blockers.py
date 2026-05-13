from __future__ import annotations

from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_recommendation_candidates import (
    build_candidate_retrieval_guard_scoring,
)


def test_negative_preference_strength_controls_block_downrank_and_ignore() -> None:
    artifact = build_candidate_retrieval_guard_scoring(
        planning=_planning(),
        fixture_inputs=_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t8",
        ),
    )

    filtered = {
        item["candidate_id"]: item["reason_codes"]
        for item in artifact["filtered_candidates"]
    }
    reviews = {
        item["candidate_id"]: item
        for item in artifact["candidate_reviews"]
    }

    assert filtered["spicy-ramen"] == ["confirmed_negative_preference"]
    assert "vegetarian-downrank" in artifact["allowed_candidate_ids"]
    assert "dessert-ignored" in artifact["allowed_candidate_ids"]
    assert reviews["vegetarian-downrank"]["soft_penalty_codes"] == [
        "negative_preference_downrank"
    ]
    assert reviews["dessert-ignored"]["soft_penalty_codes"] == []
    assert _score(artifact, "plain-ramen") > _score(artifact, "vegetarian-downrank")


def test_budget_rescue_and_availability_boundaries_are_hard_blockers() -> None:
    artifact = build_candidate_retrieval_guard_scoring(
        planning=_planning(),
        fixture_inputs=_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t8",
        ),
    )

    filtered = {
        item["candidate_id"]: item["reason_codes"]
        for item in artifact["filtered_candidates"]
    }
    trace = {
        item["candidate_id"]: item
        for item in artifact["hard_blocker_trace"]
    }

    assert filtered["over-budget"] == ["over_budget"]
    assert filtered["fried-conflict"] == ["accepted_rescue_conflict"]
    assert filtered["unavailable-shop"] == ["unavailable"]
    assert trace["over-budget"]["family"] == "budget"
    assert trace["fried-conflict"]["family"] == "rescue_conflict"
    assert trace["unavailable-shop"]["family"] == "availability"
    assert artifact["canonical_product_mutation_allowed"] is False


def test_recommendation_train_records_pr8_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 16
    assert plan["last_completed_pr_number"] == 8
    assert plan["active_pr_number"] == 9
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 8,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_negative_budget_rescue_blockers_completed_locally",
    }


def _score(artifact: dict[str, object], candidate_id: str) -> int:
    for item in artifact["scoring_trace"]:  # type: ignore[index]
        if item["candidate_id"] == candidate_id:
            return int(item["quality_score"])
    raise AssertionError(f"score_missing:{candidate_id}")


def _planning() -> dict[str, object]:
    return {
        "candidate_spec": {
            "budget_posture": {"remaining_kcal": 700, "max_candidate_kcal": 700},
            "pre_meal_planning": {},
            "swap_suggestion": {},
        }
    }


def _fixture_inputs() -> dict[str, object]:
    return {
        "recommendation_payload": {
            "current_budget_view": {"remaining_kcal": 700},
            "negative_preference_summary": {
                "items": [
                    {
                        "pattern": "spicy",
                        "status": "confirmed_negative_preference",
                        "strength": "block",
                    },
                    {
                        "pattern": "vegetarian",
                        "status": "confirmed_negative_preference",
                        "strength": "downrank",
                    },
                    {
                        "pattern": "dessert",
                        "status": "candidate",
                        "strength": "ignore",
                    },
                ]
            },
            "open_rescue_context": {
                "accepted_conflict_patterns": ["fried_chicken"]
            },
            "candidate_source_fixture": [
                _candidate("plain-ramen", "plain ramen", 620, ["ramen"]),
                _candidate("spicy-ramen", "spicy ramen", 620, ["spicy", "ramen"]),
                _candidate(
                    "vegetarian-downrank",
                    "vegetarian tofu bowl",
                    620,
                    ["vegetarian", "tofu"],
                ),
                _candidate("dessert-ignored", "dessert yogurt", 300, ["dessert"]),
                _candidate("over-budget", "large pork rice", 840, ["pork"]),
                _candidate(
                    "fried-conflict",
                    "fried chicken bento",
                    620,
                    ["fried_chicken"],
                ),
                _candidate(
                    "unavailable-shop",
                    "closed shop soba",
                    520,
                    ["soba"],
                    availability_posture="unavailable",
                ),
            ],
        }
    }


def _candidate(
    candidate_id: str,
    title: str,
    kcal: int,
    item_patterns: list[str],
    *,
    availability_posture: str = "available",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "source_type": "nearby_fixture",
        "estimated_kcal": kcal,
        "estimated_kcal_range": {"min": kcal - 80, "max": kcal},
        "item_patterns": item_patterns,
        "hard_avoid_flags": [],
        "source_refs": [f"fixture:{candidate_id}"],
        "evidence_posture": "exact",
        "availability_posture": availability_posture,
        "realistic_executable": True,
        "user_accessible": True,
    }
