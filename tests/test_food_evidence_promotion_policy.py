from __future__ import annotations

from app.nutrition.application.food_evidence_promotion_policy import (
    FOOD_EVIDENCE_PROMOTION_STAGES,
    build_food_evidence_promotion_policy,
    evaluate_food_evidence_promotion_candidate,
)


def test_food_evidence_promotion_policy_requires_staged_human_review() -> None:
    policy = build_food_evidence_promotion_policy()

    assert FOOD_EVIDENCE_PROMOTION_STAGES == (
        "review_candidate",
        "human_reviewed",
        "approved_seed_or_exact_card",
        "packet_truth",
    )
    assert policy["llm_extraction_can_approve_truth"] is False
    assert policy["food_gap_candidate_can_create_seed"] is False
    assert policy["dogfood_correction_can_create_nutrition_truth"] is False


def test_food_gap_candidate_stays_candidate_without_human_review() -> None:
    result = evaluate_food_evidence_promotion_candidate(
        {
            "candidate_id": "gap-breakfast",
            "source_class": "taiwan_tfda_open_data",
            "candidate_origin": "food_gap_register",
            "human_review_status": "needs_review",
            "requested_promotion": "approved_seed_or_exact_card",
            "provenance": {
                "dataset_name": "食品營養成分資料集",
                "retrieved_or_reviewed_date": "2026-05-04",
                "food_name": "蛋餅",
            },
        }
    )

    assert result["promotion_allowed"] is False
    assert result["current_stage"] == "review_candidate"
    assert "human_review_required" in result["blockers"]


def test_llm_extracted_candidate_cannot_approve_or_create_packet_truth() -> None:
    result = evaluate_food_evidence_promotion_candidate(
        {
            "candidate_id": "llm-normalized-boba",
            "source_class": "official_brand_chain_page",
            "candidate_origin": "llm_extraction",
            "human_review_status": "approved",
            "requested_promotion": "packet_truth",
            "llm_extracted": True,
            "provenance": {
                "source_url": "https://example.invalid/menu",
                "reviewed_date": "2026-05-04",
                "variant_name": "珍珠奶茶大杯",
                "portion_size": "large cup",
            },
        }
    )

    assert result["promotion_allowed"] is False
    assert "llm_extraction_cannot_create_packet_truth" in result["blockers"]


def test_official_exact_card_candidate_requires_complete_provenance() -> None:
    blocked = evaluate_food_evidence_promotion_candidate(
        {
            "candidate_id": "official-card",
            "source_class": "official_brand_chain_page",
            "candidate_origin": "source_registry",
            "human_review_status": "approved",
            "requested_promotion": "approved_seed_or_exact_card",
            "provenance": {
                "source_url": "https://example.invalid/menu",
                "reviewed_date": "2026-05-04",
                "variant_name": "拿鐵",
            },
        }
    )
    allowed = evaluate_food_evidence_promotion_candidate(
        {
            "candidate_id": "official-card",
            "source_class": "official_brand_chain_page",
            "candidate_origin": "source_registry",
            "human_review_status": "approved",
            "requested_promotion": "approved_seed_or_exact_card",
            "provenance": {
                "source_url": "https://example.invalid/menu",
                "reviewed_date": "2026-05-04",
                "variant_name": "拿鐵",
                "portion_size": "medium cup",
            },
        }
    )

    assert blocked["promotion_allowed"] is False
    assert "missing_required_provenance:portion_size" in blocked["blockers"]
    assert allowed["promotion_allowed"] is True
    assert allowed["next_stage"] == "approved_seed_or_exact_card"


def test_dogfood_user_correction_cannot_promote_to_nutrition_truth() -> None:
    result = evaluate_food_evidence_promotion_candidate(
        {
            "candidate_id": "user-correction-1",
            "source_class": "dogfood_user_correction",
            "candidate_origin": "dogfood_review_queue",
            "human_review_status": "approved",
            "requested_promotion": "approved_seed_or_exact_card",
            "provenance": {
                "trace_id": "trace-1",
                "turn_id": "turn-1",
                "reviewer_id": "human",
            },
        }
    )

    assert result["promotion_allowed"] is False
    assert "dogfood_user_correction_is_review_material_only" in result["blockers"]
