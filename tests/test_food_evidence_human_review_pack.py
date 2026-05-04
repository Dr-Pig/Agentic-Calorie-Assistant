from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_review_pack import (
    build_food_evidence_human_review_pack,
)


def _candidate(turn_id: str, family: str, display_text: str) -> dict:
    return {
        "candidate_id": f"food_gap_{turn_id}",
        "status": "review_candidate",
        "observed_trace_id": "accurate_intake_one_day_realistic_web_dogfood",
        "observed_turn_id": turn_id,
        "candidate_label": family,
        "gap_family": family,
        "observed_user_text_for_display_only": display_text,
        "manager_decision_summary": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "route_to_intake",
            "mutation_intent_candidate": "canonical_write",
        },
        "required_evidence_type": ["generic_anchor"],
        "source_priority_hint": ["existing_repo_seed", "taiwan_tfda_open_data"],
        "human_review_status": "needs_review",
        "promotion_allowed": False,
        "cannot_update_food_kb_truth": True,
        "cannot_create_nutrition_seed": True,
        "cannot_create_exact_card": True,
        "cannot_create_packet_truth": True,
        "cannot_create_eval_oracle": True,
        "requires_human_review_before_promotion": True,
        "reason_from_review_surface": "food evidence gap prevented realistic food logging",
        "evidence_missing_because": ["no_accepted_packet"],
        "classification_source": {
            "from_operator_review_surface": True,
            "raw_user_text_used_for_classification": False,
            "assistant_text_used_for_classification": False,
        },
    }


def _gap_register_with_unrelated_display_text() -> dict:
    return {
        "artifact_type": "accurate_intake_food_kb_gap_register",
        "status": "generated",
        "source_artifact": "accurate_intake_dogfood_operator_review_surface",
        "source_status": "diagnostic_review_with_evidence_gap",
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "food_gap_candidates": [
            _candidate("breakfast_001", "breakfast_combo", "unrelated display one"),
            _candidate(
                "lunch_001",
                "chicken_bento_rice_modifier",
                "unrelated display two",
            ),
            _candidate(
                "tea_001",
                "bubble_tea_sugar_size_modifier",
                "unrelated display three",
            ),
            _candidate(
                "dinner_basket_001",
                "luwei_listed_components",
                "unrelated display four",
            ),
        ],
    }


def _inventory() -> dict:
    return {
        "artifact_type": "accurate_intake_food_kb_v1_inventory",
        "repo_contained_seed_counts": {
            "small_anchor_total": 44,
            "generic_anchor": 40,
            "exact_item_cards": 5,
            "basket_components": 19,
        },
        "source_class_breakdown": {
            "existing_repo_seed": 49,
            "taiwan_tfda_open_data": 0,
            "official_brand_chain_page": 0,
            "open_food_facts": 0,
            "usda_fallback": 0,
            "dogfood_user_correction": 0,
            "missing_source_metadata": 49,
        },
        "missing_source_metadata_count": 49,
    }


def _quality_plan() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_quality_improvement_plan",
        "claim_scope": "fooddb_quality_planning_before_truth_promotion",
        "first_batch_review_families": [
            "breakfast_combo",
            "chicken_bento_rice_modifier",
            "bubble_tea_sugar_size_modifier",
            "luwei_listed_components",
        ],
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "bulk_food_db_expansion": False,
    }


def test_human_review_pack_keeps_pr110_gaps_review_only() -> None:
    pack = build_food_evidence_human_review_pack(
        food_gap_register=_gap_register_with_unrelated_display_text(),
        inventory=_inventory(),
        quality_plan=_quality_plan(),
    )

    assert pack["artifact_type"] == "accurate_intake_food_evidence_human_review_pack"
    assert pack["status"] == "generated"
    assert pack["claim_scope"] == "human_review_pack_before_fooddb_truth_promotion"
    assert pack["food_kb_truth_updated"] is False
    assert pack["nutrition_seed_created"] is False
    assert pack["exact_card_created"] is False
    assert pack["packet_truth_created"] is False
    assert pack["canonical_eval_promoted"] is False
    assert pack["summary"] == {
        "review_packet_count": 4,
        "candidate_count": 4,
        "promotion_ready_count": 0,
        "families_requiring_human_review": [
            "breakfast_combo",
            "chicken_bento_rice_modifier",
            "bubble_tea_sugar_size_modifier",
            "luwei_listed_components",
        ],
    }
    assert all(packet["status"] == "review_packet_only" for packet in pack["review_packets"])
    assert all(packet["promotion_allowed"] is False for packet in pack["review_packets"])
    assert all(
        candidate["promotion_allowed"] is False
        for packet in pack["review_packets"]
        for candidate in packet["candidates"]
    )


def test_human_review_pack_uses_gap_register_families_not_display_text() -> None:
    pack = build_food_evidence_human_review_pack(
        food_gap_register=_gap_register_with_unrelated_display_text(),
        inventory=_inventory(),
        quality_plan=_quality_plan(),
    )

    packets = {packet["gap_family"]: packet for packet in pack["review_packets"]}
    assert set(packets) == {
        "breakfast_combo",
        "chicken_bento_rice_modifier",
        "bubble_tea_sugar_size_modifier",
        "luwei_listed_components",
    }
    assert packets["breakfast_combo"]["candidates"][0]["observed_user_text_for_display_only"] == (
        "unrelated display one"
    )
    assert packets["breakfast_combo"]["classification_source"] == {
        "input_source": "food_gap_register",
        "raw_user_text_role": "display_only",
        "raw_user_text_used_for_classification": False,
        "assistant_text_used_for_classification": False,
    }


def test_human_review_pack_requires_item_level_human_approval() -> None:
    pack = build_food_evidence_human_review_pack(
        food_gap_register=_gap_register_with_unrelated_display_text(),
        inventory=_inventory(),
        quality_plan=_quality_plan(),
    )

    assert pack["review_policy"]["truth_promotion_gate"] == "item_level_human_approval"
    assert pack["review_policy"]["generic_anchor_estimate_policy_status"] == (
        "pending_pr116_policy_manifest"
    )
    assert pack["review_policy"]["llm_extraction_allowed"] is False
    assert pack["review_policy"]["food_gap_candidate_can_create_truth"] is False
    for packet in pack["review_packets"]:
        assert packet["review_decision_required"] == [
            "candidate_identity_review",
            "source_class_selection",
            "source_provenance_review",
            "portion_default_review",
            "estimate_point_and_range_policy_review",
            "item_level_human_approval",
        ]


def test_human_review_pack_builder_writes_only_review_artifact(tmp_path: Path) -> None:
    gap_register = tmp_path / "gap_register.json"
    inventory = tmp_path / "inventory.json"
    quality_plan = tmp_path / "quality_plan.json"
    output = tmp_path / "review_pack.json"
    gap_register.write_text(
        json.dumps(_gap_register_with_unrelated_display_text(), ensure_ascii=False),
        encoding="utf-8",
    )
    inventory.write_text(json.dumps(_inventory(), ensure_ascii=False), encoding="utf-8")
    quality_plan.write_text(json.dumps(_quality_plan(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_food_evidence_human_review_pack import main

    assert main(
        [
            "--food-gap-register",
            str(gap_register),
            "--inventory-json",
            str(inventory),
            "--quality-plan-json",
            str(quality_plan),
            "--output",
            str(output),
        ]
    ) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["nutrition_seed_created"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["summary"]["candidate_count"] == 4
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "gap_register.json",
        "inventory.json",
        "quality_plan.json",
        "review_pack.json",
    ]
