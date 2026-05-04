from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_mvp_policy import (
    build_food_evidence_mvp_policy_manifest,
    evaluate_food_evidence_mvp_policy_request,
)


def test_policy_manifest_locks_point_plus_range_for_generic_taiwan_anchors() -> None:
    manifest = build_food_evidence_mvp_policy_manifest()

    assert manifest["artifact_type"] == "accurate_intake_food_evidence_mvp_policy_manifest"
    assert manifest["claim_scope"] == "food_evidence_policy_before_first_truth_promotion"
    assert manifest["food_kb_truth_updated"] is False
    assert manifest["nutrition_seed_created"] is False
    assert manifest["exact_card_created"] is False
    assert manifest["packet_truth_created"] is False
    assert manifest["estimate_output_policy"]["generic_taiwan_anchor"] == {
        "output": "point_kcal_plus_uncertainty_range",
        "requires": [
            "source_class_compatible_with_generic_anchor",
            "source_provenance_complete",
            "portion_default_reviewed",
            "item_level_human_approval",
        ],
    }


def test_policy_manifest_separates_exact_cards_fallbacks_and_review_only_sources() -> None:
    manifest = build_food_evidence_mvp_policy_manifest()

    assert manifest["estimate_output_policy"]["exact_card"] == {
        "output": "point_kcal",
        "only_when": [
            "official_or_existing_exact_card_source",
            "brand_variant_matches",
            "portion_size_matches",
            "item_level_human_approval",
        ],
    }
    assert manifest["source_posture"]["usda_fallback"] == "fallback_generic_normalization_only"
    assert manifest["source_posture"]["open_food_facts"] == "packaged_candidate_only"
    assert manifest["source_posture"]["dogfood_user_correction"] == "review_candidate_only"
    assert manifest["truth_promotion_policy"]["approval_unit"] == "item_level"
    assert manifest["truth_promotion_policy"]["family_level_bulk_approval_allowed"] is False


def test_policy_manifest_locks_bare_and_listed_basket_behavior() -> None:
    manifest = build_food_evidence_mvp_policy_manifest()

    assert manifest["basket_policy"]["bare_basket"] == {
        "manager_expected_posture": "ask_followup",
        "estimate_allowed": False,
        "mutation_allowed": False,
    }
    assert manifest["basket_policy"]["listed_basket"] == {
        "manager_expected_posture": "estimate_components",
        "estimate_allowed_only_if": "approved_component_evidence_exists",
        "component_truth_required": True,
    }


def test_policy_request_blocks_candidate_to_truth_shortcuts() -> None:
    result = evaluate_food_evidence_mvp_policy_request(
        {
            "candidate_id": "food_gap_breakfast_001",
            "candidate_origin": "food_gap_register",
            "requested_truth_type": "generic_taiwan_anchor",
            "source_class": "taiwan_tfda_open_data",
            "human_review_status": "needs_review",
            "has_point_kcal": True,
            "has_uncertainty_range": True,
            "portion_default_reviewed": True,
        }
    )

    assert result["policy_allows_future_truth_promotion"] is False
    assert "item_level_human_approval_required" in result["blockers"]
    assert result["food_kb_truth_updated"] is False


def test_policy_request_blocks_unsupported_source_roles() -> None:
    off = evaluate_food_evidence_mvp_policy_request(
        {
            "candidate_id": "packaged_candidate",
            "requested_truth_type": "exact_card",
            "source_class": "open_food_facts",
            "human_review_status": "approved",
            "item_level_approval_id": "approval-1",
            "brand_variant_matches": True,
            "portion_size_matches": True,
        }
    )
    correction = evaluate_food_evidence_mvp_policy_request(
        {
            "candidate_id": "dogfood_correction",
            "requested_truth_type": "generic_taiwan_anchor",
            "source_class": "dogfood_user_correction",
            "human_review_status": "approved",
            "item_level_approval_id": "approval-2",
            "has_point_kcal": True,
            "has_uncertainty_range": True,
            "portion_default_reviewed": True,
        }
    )

    assert off["policy_allows_future_truth_promotion"] is False
    assert "open_food_facts_is_packaged_candidate_only" in off["blockers"]
    assert correction["policy_allows_future_truth_promotion"] is False
    assert "dogfood_user_correction_is_review_candidate_only" in correction["blockers"]


def test_policy_request_allows_reviewed_generic_anchor_without_creating_truth() -> None:
    result = evaluate_food_evidence_mvp_policy_request(
        {
            "candidate_id": "reviewed_anchor",
            "requested_truth_type": "generic_taiwan_anchor",
            "source_class": "taiwan_tfda_open_data",
            "human_review_status": "approved",
            "item_level_approval_id": "approval-3",
            "has_point_kcal": True,
            "has_uncertainty_range": True,
            "portion_default_reviewed": True,
        }
    )

    assert result["policy_allows_future_truth_promotion"] is True
    assert result["blockers"] == []
    assert result["food_kb_truth_updated"] is False
    assert result["nutrition_seed_created"] is False
    assert result["exact_card_created"] is False
    assert result["packet_truth_created"] is False


def test_policy_manifest_builder_writes_policy_artifact_only(tmp_path: Path) -> None:
    output = tmp_path / "policy.json"

    from scripts.build_accurate_intake_food_evidence_mvp_policy import main

    assert main(["--output", str(output)]) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["truth_promotion_policy"]["approval_unit"] == "item_level"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["policy.json"]
