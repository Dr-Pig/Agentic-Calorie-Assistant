from __future__ import annotations

import json
from pathlib import Path

from app.composition.food_gap_register import build_food_kb_gap_register


def _turn_review(
    turn_id: str,
    *,
    classification: str = "food_evidence_gap",
    display_text: str = "display only text",
    workflow_effect: str = "route_to_intake",
    final_action: str = "route_to_intake",
) -> dict:
    return {
        "turn_id": turn_id,
        "classification": classification,
        "display_raw_user_input": display_text,
        "manager_decision_summary": {
            "intent_type": "log_meal",
            "workflow_effect": workflow_effect,
            "final_action": final_action,
            "mutation_intent_candidate": "canonical_write",
            "target_attachment": {"mode": "new_meal"},
        },
        "evidence_gap_reason": "food evidence gap prevented realistic food logging",
        "reviewer_notes": ["canonical_write_intent_without_mutation"],
        "classification_inputs": {
            "raw_user_input_used_for_classification": False,
            "assistant_text_used_for_classification": False,
            "calories_recomputed": False,
        },
    }


def _review_surface_with_unrelated_display_text() -> dict:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_dogfood_operator_review_surface",
        "status": "diagnostic_review_with_evidence_gap",
        "source_artifact": "accurate_intake_one_day_realistic_web_dogfood",
        "source_status": "diagnostic_pass_with_evidence_gap",
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "food_kb_truth_updated": False,
        "canonical_eval_promoted": False,
        "turn_reviews": [
            _turn_review("breakfast_001", display_text="unrelated display text one"),
            _turn_review("lunch_001", display_text="unrelated display text two"),
            _turn_review("tea_001", display_text="unrelated display text three"),
            _turn_review(
                "dinner_basket_001",
                display_text="unrelated display text four",
                workflow_effect="listed_basket_commit",
                final_action="commit",
            ),
            _turn_review(
                "dinner_remove_001",
                classification="manager_context_gap",
                display_text="unrelated display text five",
                workflow_effect="correction_remove_item",
                final_action="correction_applied",
            ),
            _turn_review(
                "query_001",
                classification="query_no_mutation",
                display_text="unrelated display text six",
                workflow_effect="answer_only",
                final_action="answer_only",
            ),
        ],
    }


def test_food_gap_register_creates_review_candidates_without_truth_promotion() -> None:
    artifact = build_food_kb_gap_register(_review_surface_with_unrelated_display_text())

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_food_kb_gap_register"
    assert artifact["status"] == "generated"
    assert artifact["source_artifact"] == "accurate_intake_dogfood_operator_review_surface"
    assert artifact["source_status"] == "diagnostic_review_with_evidence_gap"
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["nutrition_seed_created"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["canonical_eval_promoted"] is False
    assert artifact["promotion_policy"]["human_review_required_before_promotion"] is True
    assert artifact["summary"]["candidate_count"] == 4
    assert artifact["summary"]["promotion_ready_count"] == 0

    families = {candidate["gap_family"] for candidate in artifact["food_gap_candidates"]}
    assert families == {
        "breakfast_combo",
        "chicken_bento_rice_modifier",
        "bubble_tea_sugar_size_modifier",
        "luwei_listed_components",
    }
    assert all(candidate["status"] == "review_candidate" for candidate in artifact["food_gap_candidates"])
    assert all(candidate["promotion_allowed"] is False for candidate in artifact["food_gap_candidates"])
    assert all(
        candidate["cannot_update_food_kb_truth"] is True
        for candidate in artifact["food_gap_candidates"]
    )
    assert all(
        candidate["cannot_create_nutrition_seed"] is True
        for candidate in artifact["food_gap_candidates"]
    )


def test_food_gap_register_uses_turn_review_structure_not_raw_display_text() -> None:
    artifact = build_food_kb_gap_register(_review_surface_with_unrelated_display_text())
    candidates = {
        candidate["observed_turn_id"]: candidate
        for candidate in artifact["food_gap_candidates"]
    }

    assert candidates["breakfast_001"]["gap_family"] == "breakfast_combo"
    assert candidates["breakfast_001"]["observed_user_text_for_display_only"] == (
        "unrelated display text one"
    )
    assert candidates["breakfast_001"]["classification_source"] == {
        "from_operator_review_surface": True,
        "raw_user_text_used_for_classification": False,
        "assistant_text_used_for_classification": False,
    }
    assert candidates["lunch_001"]["gap_family"] == "chicken_bento_rice_modifier"
    assert candidates["tea_001"]["gap_family"] == "bubble_tea_sugar_size_modifier"
    assert candidates["dinner_basket_001"]["gap_family"] == "luwei_listed_components"


def test_food_gap_register_keeps_manager_context_gap_out_of_food_truth_candidates() -> None:
    artifact = build_food_kb_gap_register(_review_surface_with_unrelated_display_text())

    non_candidates = {
        item["observed_turn_id"]: item for item in artifact["non_candidate_turns"]
    }
    assert non_candidates["dinner_remove_001"]["classification"] == "manager_context_gap"
    assert non_candidates["dinner_remove_001"]["reason"] == (
        "turn is not a food_evidence_gap review candidate"
    )
    assert non_candidates["query_001"]["classification"] == "query_no_mutation"
    assert artifact["summary"]["non_candidate_count"] == 2


def test_food_gap_register_builder_writes_only_gap_register_artifact(tmp_path: Path) -> None:
    review_path = tmp_path / "operator_review.json"
    output_path = tmp_path / "food_gap_register.json"
    review_path.write_text(
        json.dumps(_review_surface_with_unrelated_display_text(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_food_gap_register import main

    exit_code = main(["--operator-review-json", str(review_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["local_only"] is True
    assert artifact["do_not_commit"] is True
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["summary"]["candidate_count"] == 4
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "food_gap_register.json",
        "operator_review.json",
    ]
