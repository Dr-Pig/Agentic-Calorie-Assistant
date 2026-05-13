from __future__ import annotations

from app.advanced_shadow_lab.product_lab_recommendation_candidate_sources import (
    recommendation_source_candidates,
)
from app.recommendation.application.candidate_source_port import (
    build_recommendation_candidate_source_port_contract,
    normalize_recommendation_candidate_sources,
    recommendation_candidate_source_port_blockers,
)


def test_candidate_source_port_contract_names_sources_without_scoring() -> None:
    contract = build_recommendation_candidate_source_port_contract()

    assert contract["artifact_type"] == "recommendation_candidate_source_port_contract"
    assert contract["source_families"] == [
        "fooddb",
        "memory",
        "budget",
        "rescue",
        "reusable_meal",
    ]
    assert contract["candidate_fields_required"] == [
        "candidate_id",
        "title",
        "source_family",
        "source_refs",
    ]
    assert contract["may_score_or_rank_candidates"] is False
    assert contract["may_filter_hard_blockers"] is False
    assert contract["canonical_product_mutation_allowed"] is False
    assert contract["blockers"] == []


def test_candidate_source_port_normalizes_fooddb_memory_and_context_views() -> None:
    artifact = normalize_recommendation_candidate_sources(
        payload={
            "candidate_source_fixture": [
                {
                    "candidate_id": "fooddb-1",
                    "title": "FoodDB chicken bento",
                    "source_type": "fooddb",
                    "source_refs": ["fooddb:chicken-bento"],
                }
            ],
            "current_budget_view": {"remaining_kcal": 650},
            "open_rescue_context": {"accepted_conflict_patterns": ["fried"]},
        },
        memory_context_pack={
            "entries": [
                {
                    "record_id": "memory-1",
                    "memory_type": "golden_order",
                    "summary": "Reliable remembered bento.",
                    "store_name": "FamilyMart",
                    "item_names": ["chicken bento"],
                    "estimated_kcal": 520,
                }
            ]
        },
        reusable_meal_context_pack={
            "reusable_meal_candidates": [
                {
                    "entity_id": "ufe-fried-rice",
                    "display_name": "Mom fried rice",
                    "source_refs": ["memory_record:reusable-meal-hint-1"],
                }
            ]
        },
    )

    assert artifact["status"] == "pass"
    assert artifact["candidate_source_ids"] == [
        "fooddb-1",
        "memory-1",
        "ufe-fried-rice",
    ]
    assert [item["source_family"] for item in artifact["candidate_sources"]] == [
        "fooddb",
        "memory",
        "reusable_meal",
    ]
    assert artifact["source_context_views"]["budget"] == {"remaining_kcal": 650}
    assert artifact["source_context_views"]["rescue"] == {
        "accepted_conflict_patterns": ["fried"]
    }
    assert artifact["may_score_or_rank_candidates"] is False
    assert artifact["may_filter_hard_blockers"] is False
    assert artifact["blockers"] == []


def test_candidate_source_port_blocks_scoring_and_raw_transcript_leaks() -> None:
    assert recommendation_candidate_source_port_blockers(
        {
            "candidate_sources": [],
            "allowed_candidate_ids": ["fooddb-1"],
            "raw_transcript": [{"role": "user", "content": "leak"}],
        }
    ) == [
        "candidate_source_port.forbidden_field:allowed_candidate_ids",
        "candidate_source_port.forbidden_field:raw_transcript",
    ]


def test_product_lab_candidate_sources_use_normalized_port() -> None:
    candidates = recommendation_source_candidates(
        payload={
            "candidate_source_fixture": [
                {
                    "candidate_id": "fooddb-1",
                    "title": "FoodDB chicken bento",
                    "source_type": "fooddb",
                    "source_refs": ["fooddb:chicken-bento"],
                }
            ]
        },
        memory_context_pack={
            "entries": [
                {
                    "record_id": "memory-1",
                    "memory_type": "golden_order",
                    "summary": "Reliable remembered bento.",
                    "store_name": "FamilyMart",
                    "item_names": ["chicken bento"],
                    "estimated_kcal": 520,
                }
            ]
        },
    )

    assert [candidate["candidate_id"] for candidate in candidates] == [
        "fooddb-1",
        "memory-1",
    ]
    assert candidates[0]["source_family"] == "fooddb"
    assert candidates[1]["source_family"] == "memory"


def test_recommendation_train_records_pr6_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 18
    assert plan["last_completed_pr_number"] >= 6
    assert plan["active_pr_number"] >= 7
    assert {
        "pr_number": 6,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_candidate_source_port_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]
