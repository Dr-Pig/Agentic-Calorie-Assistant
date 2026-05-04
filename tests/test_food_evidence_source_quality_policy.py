from __future__ import annotations

from app.nutrition.application.food_source_quality_policy import (
    FOOD_EVIDENCE_SOURCE_CLASSES,
    build_food_evidence_source_quality_policy,
)


def test_food_evidence_source_quality_policy_defines_required_source_classes() -> None:
    policy = build_food_evidence_source_quality_policy()

    assert policy["artifact_type"] == "accurate_intake_food_evidence_source_quality_policy"
    assert policy["claim_scope"] == "source_quality_gate_before_food_kb_expansion"
    assert policy["food_kb_truth_updated"] is False
    assert policy["nutrition_seed_created"] is False
    assert policy["exact_card_created"] is False
    assert policy["canonical_eval_promoted"] is False
    assert set(policy["source_classes"]) == {
        "existing_repo_seed",
        "taiwan_tfda_open_data",
        "official_brand_chain_page",
        "open_food_facts",
        "usda_fallback",
        "dogfood_user_correction",
    }
    assert set(FOOD_EVIDENCE_SOURCE_CLASSES) == set(policy["source_classes"])


def test_food_evidence_source_quality_policy_prevents_user_correction_as_truth() -> None:
    policy = build_food_evidence_source_quality_policy()
    user_correction = policy["source_classes"]["dogfood_user_correction"]

    assert user_correction["role"] == "review_candidate"
    assert "gap_candidate" in user_correction["can_support"]
    assert "human_label" in user_correction["can_support"]
    assert "nutrition_truth" in user_correction["cannot_support_until_approved"]
    assert user_correction["human_review_required"] is True


def test_food_evidence_source_quality_policy_separates_exact_and_fallback_sources() -> None:
    policy = build_food_evidence_source_quality_policy()
    official = policy["source_classes"]["official_brand_chain_page"]
    usda = policy["source_classes"]["usda_fallback"]
    off = policy["source_classes"]["open_food_facts"]

    assert official["role"] == "exact_card"
    assert official["can_support"] == ["exact_item_evidence"]
    assert {"source_url", "reviewed_date", "variant_name", "portion_size"} <= set(
        official["required_provenance"]
    )

    assert usda["role"] == "fallback_generic_normalization"
    assert usda["confidence_posture"] == "medium"
    assert usda["caveats"] == ["non_taiwan_specific"]

    assert off["confidence_posture"] == "variable"
    assert off["requires_quality_flags"] is True
    assert "candidate_only_unless_quality_flags_pass" in off["can_support"]
