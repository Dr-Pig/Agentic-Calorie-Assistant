from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from scripts.build_accurate_intake_product_loop_handoff_v3 import (
    build_product_loop_handoff_v3,
)


def _macro_complete_card(**overrides: object) -> dict[str, object]:
    card = {
        "item_id": "exact_test_chocolate_milk_400ml",
        "title": "Test Chocolate Milk 400ml",
        "aliases": ["Test Chocolate Milk 400ml"],
        "brand": "Test Brand",
        "serving_basis": "400ml",
        "kcal": 300,
        "protein_g": 12,
        "carb_g": 48,
        "fat_g": 6,
        "macro_basis": "per_package",
        "macro_confidence": "high",
        "macro_source_strength": "exact_item_seed",
        "kcal_band": "per_package",
    }
    card.update(overrides)
    return card


def _generic_common_anchor(**overrides: object) -> dict[str, object]:
    anchor = {
        "record_kind": "generic_anchor",
        "anchor_id": "generic_test_chicken_bento",
        "canonical_name": "Test Chicken Bento",
        "aliases": ["Test Chicken Bento"],
        "runtime_role": "common_serving_anchor",
        "runtime_truth_allowed": True,
        "composition_posture": "estimable_generic_meal",
        "serving_basis": "common_serving",
        "portion_basis": {"portion_unit": "box", "portion_quantity": 1},
        "kcal_point": 780,
        "kcal_range": [650, 900],
        "source_provenance": {
            "source_id": "test_small_anchor_store",
            "source_file": "test_small_anchor_store.json",
            "record_id": "generic_test_chicken_bento",
        },
        "approval_metadata": {
            "approval_mode": "internal_seed_batch_approved",
            "runtime_truth_allowed": True,
        },
        "runtime_usage_boundary": "generic_range_estimate_only_not_exact",
    }
    anchor.update(overrides)
    return anchor


def _listed_component_anchor(**overrides: object) -> dict[str, object]:
    anchor = {
        "record_kind": "generic_anchor",
        "anchor_id": "listed_test_tofu_dried",
        "canonical_name": "Test Dried Tofu",
        "aliases": ["Test Dried Tofu"],
        "runtime_role": "common_serving_anchor",
        "runtime_truth_allowed": True,
        "composition_posture": "listed_item_component",
        "serving_basis": "common_serving",
        "portion_basis": {"portion_unit": "piece", "portion_quantity": 1},
        "kcal_point": 95,
        "kcal_range": [70, 120],
        "source_provenance": {
            "source_id": "test_tfda_source",
            "source_file": "test_source.xlsx",
            "record_id": "listed_test_tofu_dried",
        },
        "approval_metadata": {
            "approval_mode": "batch_policy_approved",
            "runtime_truth_allowed": True,
        },
        "runtime_usage_boundary": "listed_component_only",
    }
    anchor.update(overrides)
    return anchor


def _product_loop_evidence() -> dict[str, object]:
    return {
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "local_web_candidate": {
            "local_web_self_use_candidate_v2": {
                "candidate_prepared": True,
                "blockers": [],
                "appshell_browser_evidence_chain": {
                    "browser_artifact_count": 7,
                    "browser_executed_count": 7,
                    "all_required_browser_artifacts_executed": True,
                    "product_pages_self_use_flow_checked": True,
                    "today_macro_runtime_mirror_checked": True,
                    "renderer_source_closure_checked": True,
                    "context_target_browser_closure_checked": True,
                    "body_noplan_degraded_checked": True,
                    "body_observation_same_truth_checked": True,
                    "live_llm_invoked": False,
                    "fooddb_evidence_used": False,
                    "websearch_evidence_used": False,
                    "runtime_truth_changed": False,
                    "mutation_changed": False,
                    "frontend_semantic_owner": False,
                },
            }
        },
        "browser_fixture_dogfood": {
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "fixture_fooddb_evidence_used": True,
            "fooddb_evidence_used": False,
            "fooddb_evidence_used_normalized_for_local_review": True,
            "manager_dogfood_summary": {
                "macro_present_evidence_seen": True,
                "macro_missing_evidence_seen": True,
            },
            "real_fooddb_pass_claimed": False,
        },
        "local_dogfood_hygiene": {"status": "pass"},
        "browser_realistic_dogfood": {
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "one_day_realistic_dogfood": {
            "one_day_realistic_web_dogfood": {
                "status": "pass",
                "live_provider_called": False,
                "kimi_activated": False,
                "production_db_touched": False,
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
                "real_fooddb_pass_claimed": False,
                "dogfood_pass": False,
                "blockers": [],
                "evidence": {
                    "approved_fooddb_evidence_fixture_used": True,
                    "fooddb_evidence_used": True,
                    "macro_present_evidence_seen": True,
                    "macro_missing_evidence_seen": True,
                },
            }
        },
        "operator_review": {
            "artifact_type": "accurate_intake_dogfood_operator_review_surface",
            "status": "browser_diagnostic_review_with_fixture_evidence_gap",
            "claim_scope": "local_dogfood_operator_review_surface",
            "local_only": True,
            "do_not_commit": True,
            "food_kb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "classification_policy": {
                "food_kb_truth_update_allowed": False,
                "frontend_semantic_owner": False,
            },
        },
        "mvp_gate": {"status": "pass"},
    }


def test_build_approved_packet_ready_artifact_uses_macro_complete_exact_card() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    metadata = artifact["approved_packet_ready_evidence_artifact"]
    assert artifact["artifact_type"] == "accurate_intake_approved_packet_ready_fooddb_artifact"
    assert artifact["producer_track"] == "FoodDB"
    assert artifact["fixture_or_real"] == "real"
    assert artifact["ready_for_other_tracks"] is True
    assert metadata["fixture_or_real"] == "real"
    assert metadata["source_quality"] == "packet_ready_approved"
    assert metadata["ready_for_product_loop"] is True
    macro_contract = metadata["macro_contract"]
    assert macro_contract["packet_fields"] == [
        "protein_g",
        "carbs_g",
        "fat_g",
        "macro_visibility_status",
        "macro_source_basis",
        "macro_confidence",
    ]
    assert macro_contract["macro_truth_owner"] == "fooddb_approved_packet"
    assert macro_contract["missing_macro_policy"] == "preserve_null_do_not_invent"
    assert macro_contract["macro_runtime_policy"] == {
        "calorie_first": True,
        "macro_aware": True,
        "missing_macro_blocks_kcal_logging": False,
        "manager_may_infer_macro_from_food_name": False,
    }
    source_policy = macro_contract["source_class_policy"]
    assert source_policy["exact_brand_item"]["macro_truth_allowed"] is True
    assert source_policy["generic_common_serving"]["allowed_macro_values"] == [
        "point",
        "range",
        "null_unknown",
    ]
    assert source_policy["listed_component"]["preferred_macro_granularity"] == "per_unit"
    assert source_policy["basket_family_alias_modifier"]["macro_truth_allowed"] is False
    assert source_policy["source_evidence_candidate"]["macro_truth_allowed"] is False
    assert source_policy["source_evidence_candidate"]["source_classes"] == [
        "TFDA_per_100g",
        "USDA",
        "OpenFoodFacts",
        "WebSearch",
    ]
    shadow_schema = macro_contract["shadow_schema"]
    generic_fields = shadow_schema["generic_common_serving"]["macro_fields"]
    assert "protein_g_point" in generic_fields
    assert "protein_g_range" in generic_fields
    assert "carbs_g_point" in generic_fields
    assert "carbs_g_range" in generic_fields
    assert "fat_g_point" in generic_fields
    assert "fat_g_range" in generic_fields
    assert "macro_source_strength" in generic_fields
    assert shadow_schema["generic_common_serving"]["values_may_be_null"] is True
    component_fields = shadow_schema["listed_component"]["macro_fields"]
    assert "protein_g_per_unit" in component_fields
    assert "carbs_g_per_unit" in component_fields
    assert "fat_g_per_unit" in component_fields
    assert shadow_schema["basket_family_alias_modifier"]["macro_fields"] == []
    assert (
        shadow_schema["source_evidence_candidate"]["runtime_truth_allowed"]
        is False
    )

    item = artifact["packet_ready_items"][0]
    assert item["source_lane"] == "exact_item_card"
    assert item["runtime_truth_allowed"] is True
    assert item["kcal_point"] == 300
    assert item["protein_g"] == 12
    assert item["carbs_g"] == 48
    assert item["fat_g"] == 6
    assert item["macro_visibility_status"] == "visible"
    assert item["macro_source_basis"] == "exact_item_seed_label"
    assert item["macro_confidence"] == "high"


def test_build_approved_packet_ready_artifact_preserves_fractional_exact_label_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[
            _macro_complete_card(
                item_id="exact_test_fractional_macro_label",
                kcal=42.7,
                protein_g=5.7,
                carb_g=0.1,
                fat_g=0.3,
            )
        ],
        small_anchor_records=[_generic_common_anchor(), _listed_component_anchor()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    item = artifact["packet_ready_items"][0]
    assert item["kcal_point"] == 42.7
    assert item["kcal_range"] == [42.7, 42.7]
    assert item["protein_g"] == 5.7
    assert item["carbs_g"] == 0.1
    assert item["fat_g"] == 0.3
    assert item["macro_visibility_status"] == "visible"


def test_build_approved_packet_ready_artifact_includes_minimal_triad_lanes() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card()],
        small_anchor_records=[_generic_common_anchor(), _listed_component_anchor()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["ready_for_other_tracks"] is True
    assert artifact["summary"]["packet_ready_item_count"] == 3
    assert artifact["summary"]["packet_ready_lane_counts"] == {
        "exact_item_card": 1,
        "generic_common_serving": 1,
        "listed_component": 1,
    }
    by_lane = {item["source_lane"]: item for item in artifact["packet_ready_items"]}
    generic = by_lane["generic_common_serving"]
    assert generic["runtime_truth_allowed"] is True
    assert generic["kcal_point"] == 780
    assert generic["kcal_range"] == [650, 900]
    assert generic["protein_g"] is None
    assert generic["carbs_g"] is None
    assert generic["fat_g"] is None
    assert generic["macro_visibility_status"] == "hidden_missing_source"
    assert generic["macro_source_basis"] == "unknown"
    assert generic["macro_confidence"] == "unknown"
    assert generic["runtime_usage_boundary"] == "generic_range_estimate_only_not_exact"

    component = by_lane["listed_component"]
    assert component["runtime_truth_allowed"] is True
    assert component["kcal_point"] == 95
    assert component["kcal_range"] == [70, 120]
    assert component["protein_g"] is None
    assert component["carbs_g"] is None
    assert component["fat_g"] is None
    assert component["macro_visibility_status"] == "hidden_missing_source"
    assert component["runtime_usage_boundary"] == "listed_component_only"
    assert component["approval_metadata"]["approval_scope"] == (
        "minimal_current_shell_listed_component_macro_unknown"
    )


def test_build_approved_packet_ready_artifact_blocks_without_required_triad_lanes() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card()],
        small_anchor_records=[_generic_common_anchor()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    assert artifact["status"] == "blocked_missing_packet_ready_lane"
    assert artifact["ready_for_other_tracks"] is False
    assert "no_packet_ready_listed_component" in artifact["blockers"]
    assert artifact["summary"]["packet_ready_lane_counts"] == {
        "exact_item_card": 1,
        "generic_common_serving": 1,
        "listed_component": 0,
    }


def test_build_approved_packet_ready_artifact_blocks_without_macro_complete_card() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        exact_item_cards=[_macro_complete_card(protein_g=0, carb_g=0, fat_g=0)],
        small_anchor_records=[_generic_common_anchor(), _listed_component_anchor()],
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    metadata = artifact["approved_packet_ready_evidence_artifact"]
    assert artifact["status"] == "blocked_missing_packet_ready_lane"
    assert artifact["ready_for_other_tracks"] is False
    assert metadata["ready_for_product_loop"] is False
    assert "no_macro_complete_exact_item_card" in artifact["blockers"]


def test_default_repo_artifact_builds_from_tracked_exact_item_seed() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["ready_for_other_tracks"] is True
    assert artifact["summary"]["source_file"] == "app/knowledge/exact_item_cards_tw.json"
    assert artifact["summary"]["small_anchor_source_file"] == "app/knowledge/small_anchor_store_tw.json"
    assert artifact["summary"]["packet_ready_item_count"] == 3
    assert artifact["summary"]["packet_ready_lane_counts"] == {
        "exact_item_card": 1,
        "generic_common_serving": 1,
        "listed_component": 1,
    }
    assert artifact["summary"]["available_packet_ready_lane_counts"] == {
        "exact_item_card": 226,
        "generic_common_serving": 400,
        "listed_component": 350,
    }
    by_lane = {item["source_lane"]: item for item in artifact["packet_ready_items"]}
    assert by_lane["exact_item_card"]["macro_visibility_status"] == "visible"
    assert by_lane["generic_common_serving"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_lane["listed_component"]["macro_visibility_status"] == "hidden_missing_source"


def test_full_current_shell_profile_includes_all_approved_packet_ready_lanes() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )

    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["summary"]["selection_profile"] == "full_current_shell"
    assert artifact["summary"]["packet_ready_item_count"] == 976
    assert artifact["summary"]["packet_ready_lane_counts"] == {
        "exact_item_card": 226,
        "generic_common_serving": 400,
        "listed_component": 350,
    }
    assert artifact["summary"]["available_packet_ready_lane_counts"] == {
        "exact_item_card": 226,
        "generic_common_serving": 400,
        "listed_component": 350,
    }
    assert artifact["manager_packet_forbidden_inputs"] == [
        "raw_source_rows",
        "candidate_only_records",
        "full_fooddb_dump",
        "websearch_snippets_as_truth",
        "dogfood_feedback",
        "macro_values_inferred_from_name_or_kcal",
    ]

    by_id = {item["item_id"]: item for item in artifact["packet_ready_items"]}
    assert by_id["exact_yuhofang_sweet_potato_crisps_60g"]["macro_visibility_status"] == "visible"
    assert by_id["generic_drink_guava_juice_300ml"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_2f20784934e5"
    )
    assert by_id["generic_drink_guava_juice_300ml"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["generic_drink_boba_milk_tea_half_sugar_700ml"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_4a1a20da8abc"
    )
    assert by_id["generic_drink_boba_milk_tea_half_sugar_700ml"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["generic_snack_dark_chocolate_85_serving"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_4c40318f3188"
    )
    assert by_id["generic_snack_dark_chocolate_85_serving"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["generic_ready_retort_rice_porridge_bowl"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_3f3360c98a6b"
    )
    assert by_id["generic_ready_retort_rice_porridge_bowl"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["generic_sauce_satay_tbsp"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_b6d1810164e4"
    )
    assert by_id["generic_sauce_satay_tbsp"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["generic_spread_black_sesame_bread_spread_tbsp"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_ca15997d367b"
    )
    assert by_id["generic_spread_black_sesame_bread_spread_tbsp"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["exact_weichuan_prince_cup_noodle_pork_52g"]["source_provenance"]["source_file"] == (
        "app/knowledge/exact_item_cards_tw_batch_002.json"
    )
    assert by_id["exact_aisin_fried_squid_popcorn_100g"]["source_provenance"]["source_file"] == (
        "app/knowledge/exact_item_cards_tw_batch_003.json"
    )
    assert by_id["exact_mr_brown_platinum_coffee_240ml"]["source_provenance"]["source_file"] == (
        "app/knowledge/exact_item_cards_tw_batch_004.json"
    )
    assert by_id["exact_quaker_unsweetened_nutrition_drink_250ml"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_005.json"
    assert by_id["exact_oak_full_cream_milk_powder_32g"]["source_provenance"]["source_file"] == (
        "app/knowledge/exact_item_cards_tw_batch_006.json"
    )
    assert by_id["exact_oak_full_cream_milk_powder_32g"]["macro_visibility_status"] == "visible"
    assert by_id["exact_lamole_focaccia_crackers_25g"]["source_provenance"]["source_file"] == (
        "app/knowledge/exact_item_cards_tw_batch_007.json"
    )
    assert by_id["exact_lamole_focaccia_crackers_25g"]["macro_visibility_status"] == "visible"
    assert by_id["exact_ovaltine_malt_drink_powder_30g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_008.json"
    assert by_id["exact_ovaltine_malt_drink_powder_30g"]["macro_visibility_status"] == "visible"
    assert by_id["exact_popochacha_clam_chili_ramen_115g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_009.json"
    assert by_id["exact_popochacha_clam_chili_ramen_115g"]["macro_visibility_status"] == "visible"
    assert by_id["exact_wayne_mocha_coffee_320ml"]["source_provenance"]["source_file"] == (
        "app/knowledge/exact_item_cards_tw_batch_010.json"
    )
    assert by_id["exact_wayne_mocha_coffee_320ml"]["macro_visibility_status"] == "visible"
    assert by_id["exact_quaker_complete_nutrition_plant_protein_250ml"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_011.json"
    assert (
        by_id["exact_quaker_complete_nutrition_plant_protein_250ml"][
            "macro_visibility_status"
        ]
        == "visible"
    )
    assert by_id["exact_ferrero_rocher_milk_chocolate_bar_18g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_012.json"
    assert (
        by_id["exact_ferrero_rocher_milk_chocolate_bar_18g"][
            "macro_visibility_status"
        ]
        == "visible"
    )
    assert by_id["exact_so_good_high_protein_almond_milk_unsweetened_200ml"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_013.json"
    assert (
        by_id["exact_so_good_high_protein_almond_milk_unsweetened_200ml"][
            "macro_visibility_status"
        ]
        == "visible"
    )
    assert by_id["exact_skyflakes_cream_sandwich_crackers_30g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_014.json"
    assert (
        by_id["exact_skyflakes_cream_sandwich_crackers_30g"][
            "macro_visibility_status"
        ]
        == "visible"
    )
    assert by_id["exact_imei_cream_puffs_milk_65g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_015.json"
    assert by_id["exact_imei_cream_puffs_milk_65g"]["macro_visibility_status"] == (
        "visible"
    )
    assert by_id["exact_red_cow_whey_protein_cocoa_35g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_016.json"
    assert by_id["exact_red_cow_whey_protein_cocoa_35g"]["macro_visibility_status"] == (
        "visible"
    )
    assert by_id["exact_unipresident_ab_yogurt_drink_strawberry_300_6ml"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_017.json"
    assert by_id["exact_unipresident_ab_yogurt_drink_strawberry_300_6ml"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["exact_mr_brown_deep_roast_latte_240ml"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_018.json"
    assert by_id["exact_mr_brown_deep_roast_latte_240ml"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["exact_teasers_salted_caramel_chocolate_50g"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_019.json"
    assert by_id["exact_teasers_salted_caramel_chocolate_50g"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["exact_paldo_kimchi_ramen_120g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_020.json"
    assert by_id["exact_paldo_kimchi_ramen_120g"]["macro_visibility_status"] == (
        "visible"
    )
    assert by_id["exact_knorr_mentaiko_pasta_sauce_140g"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_021.json"
    assert by_id["exact_knorr_mentaiko_pasta_sauce_140g"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["exact_sanxing_spicy_grilled_eel_53g"]["source_provenance"][
        "source_file"
    ] == "app/knowledge/exact_item_cards_tw_batch_022.json"
    assert by_id["exact_sanxing_spicy_grilled_eel_53g"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["exact_weiwei_a_black_garlic_tonkotsu_noodle_99g"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_023.json"
    assert by_id["exact_weiwei_a_black_garlic_tonkotsu_noodle_99g"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["exact_klim_family_triple_calcium_milk_powder_42g"][
        "source_provenance"
    ]["source_file"] == "app/knowledge/exact_item_cards_tw_batch_024.json"
    assert by_id["exact_klim_family_triple_calcium_milk_powder_42g"][
        "macro_visibility_status"
    ] == "visible"
    assert by_id["generic_staple_meat_floss_triangle_rice_ball"]["kcal_point"] == 235
    assert by_id["generic_staple_meat_floss_triangle_rice_ball"]["kcal_range"] == [190, 300]
    assert by_id["generic_staple_meat_floss_triangle_rice_ball"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_market_frozen_ham_fried_rice_pack"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_e8b714605f7d"
    assert (
        by_id["generic_market_frozen_ham_fried_rice_pack"][
            "macro_visibility_status"
        ]
        == "hidden_missing_source"
    )
    assert by_id["generic_dessert_cheesecake_slice"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_ca1b9f035cd0"
    assert by_id["generic_dessert_cheesecake_slice"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_staple_ham_fried_rice_plate"]["kcal_point"] == 648
    assert by_id["generic_staple_ham_fried_rice_plate"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_bakery_pineapple_bun_one"]["kcal_point"] == 291
    assert by_id["generic_bakery_pineapple_bun_one"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_street_coffin_bread_one"]["kcal_point"] == 522
    assert by_id["generic_street_coffin_bread_one"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_noodle_frozen_udon_serving"]["kcal_point"] == 251
    assert by_id["generic_noodle_frozen_udon_serving"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_1ad9def46830"
    )
    assert by_id["generic_noodle_frozen_udon_serving"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_instant_noodle_beef_pack"]["source_provenance"]["source_file"] == (
        "app/knowledge/tfda_per100g_source_evidence_tw.json"
    )
    assert by_id["generic_instant_noodle_beef_pack"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_d43809a16565"
    )
    assert by_id["generic_instant_noodle_beef_pack"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_staple_beef_dumplings_10pc"]["kcal_point"] == 532
    assert by_id["generic_staple_beef_dumplings_10pc"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_staple_meat_zongzi_one"]["kcal_point"] == 467
    assert by_id["generic_staple_meat_zongzi_one"]["kcal_range"] == [360, 650]
    assert by_id["generic_staple_meat_zongzi_one"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_staple_white_rice_bowl"]["kcal_point"] == 366
    assert by_id["generic_staple_white_rice_bowl"]["source_provenance"]["source_url"] == (
        "https://data.gov.tw/dataset/8543"
    )
    assert by_id["generic_staple_white_rice_bowl"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["generic_drink_cola_can"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_1ef4d8a3cdff"
    )
    assert by_id["generic_drink_cola_can"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_egg_dumpling"]["kcal_point"] == 55
    assert by_id["listed_item_egg_dumpling"]["source_lane"] == "listed_component"
    assert by_id["listed_item_egg_dumpling"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["listed_item_shrimp_roll"]["kcal_point"] == 46
    assert by_id["listed_item_shrimp_roll"]["macro_visibility_status"] == "hidden_missing_source"
    assert by_id["listed_item_small_dried_tofu_piece"]["kcal_point"] == 62
    assert by_id["listed_item_small_dried_tofu_piece"]["kcal_range"] == [45, 85]
    assert by_id["listed_item_small_dried_tofu_piece"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_boiled_egg_one"]["kcal_point"] == 79
    assert by_id["listed_item_boiled_egg_one"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_pork_large_intestine_100g"]["kcal_point"] == 198
    assert by_id["listed_item_pork_large_intestine_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_salmon_sashimi_100g"]["kcal_point"] == 222
    assert by_id["listed_item_salmon_sashimi_100g"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_bf89af0046a3"
    )
    assert by_id["listed_item_salmon_sashimi_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_chicken_breast_100g"]["kcal_point"] == 119
    assert by_id["listed_item_chicken_breast_100g"]["source_provenance"]["source_url"] == (
        "https://data.gov.tw/dataset/8543"
    )
    assert by_id["listed_item_chicken_breast_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_modifier_curry_cube_20g"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_39f910777a64"
    )
    assert by_id["listed_modifier_curry_cube_20g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_white_cutlassfish_100g"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_316868e6ad0c"
    assert by_id["listed_item_white_cutlassfish_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_chicken_sausage_small_one"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_77ad9523ab48"
    assert by_id["listed_item_chicken_sausage_small_one"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_milkfish_ball_100g"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_a721bd05495e"
    assert by_id["listed_item_milkfish_ball_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_tea_egg_one"]["source_refs"][0]["source_evidence_id"] == (
        "tfda_per100g_948e3e0b62f9"
    )
    assert by_id["listed_item_tea_egg_one"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_taiwan_tilapia_fillet_100g"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_7bdcd1b3f43b"
    assert by_id["listed_item_taiwan_tilapia_fillet_100g"][
        "macro_visibility_status"
    ] == "hidden_missing_source"
    assert by_id["listed_item_canned_corn_sauce_100g"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_bbf88fb4da7f"
    assert by_id["listed_item_canned_corn_sauce_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_modifier_five_spice_powder_5g"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_e3d91ad4f37e"
    assert by_id["listed_modifier_five_spice_powder_5g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["listed_item_frozen_chicken_nuggets_100g"]["source_refs"][0][
        "source_evidence_id"
    ] == "tfda_per100g_812b67bc10c8"
    assert by_id["listed_item_frozen_chicken_nuggets_100g"]["macro_visibility_status"] == (
        "hidden_missing_source"
    )
    assert by_id["custom_drink_boba_milk_tea"]["source_lane"] == "generic_common_serving"
    assert by_id["listed_item_milkfish_ball"]["source_lane"] == "listed_component"
    assert all("raw_row" not in item for item in artifact["packet_ready_items"])


def test_artifact_is_accepted_by_product_loop_handoff_validation_only() -> None:
    fooddb_artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json",
    )

    handoff = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=fooddb_artifact,
    )

    assert handoff["status"] == "product_loop_handoff_ready_for_fdb_integration_validation"
    assert handoff["ready_for_fdb_integration"] is True
    assert handoff["fooddb_validation"]["metadata"]["macro_contract"][
        "missing_macro_policy"
    ] == "preserve_null_do_not_invent"
    assert handoff["fooddb_evidence_used"] is False
    assert handoff["real_fooddb_pass_claimed"] is False
    assert handoff["dogfood_pass"] is False


def test_approved_packet_ready_fooddb_artifact_cli_writes_json(tmp_path: Path) -> None:
    cards_path = tmp_path / "exact_item_cards.json"
    output_path = tmp_path / "approved_packet_ready_fooddb.json"
    cards_path.write_text(
        json.dumps({"cards": [_macro_complete_card()]}, ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_approved_packet_ready_fooddb_artifact import main

    exit_code = main(
        [
            "--exact-item-cards",
            str(cards_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["approved_packet_ready_evidence_artifact"]["path"] == str(output_path)
    assert artifact["summary"]["packet_ready_item_count"] == 3


def test_approved_packet_ready_fooddb_artifact_cli_can_write_full_current_shell_profile(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "approved_packet_ready_fooddb_full.json"

    from scripts.build_accurate_intake_approved_packet_ready_fooddb_artifact import main

    exit_code = main(
        [
            "--selection-profile",
            "full_current_shell",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["summary"]["selection_profile"] == "full_current_shell"
    assert artifact["summary"]["packet_ready_item_count"] == 976


def test_runbook_documents_minimal_fooddb_packet_ready_artifact() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "build_accurate_intake_approved_packet_ready_fooddb_artifact.py" in runbook
    assert "--fooddb-artifact artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json" in runbook
