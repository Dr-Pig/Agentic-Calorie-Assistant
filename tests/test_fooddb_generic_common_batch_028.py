from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_drink_loose_rice_milk_cup",
    "generic_drink_brown_rice_milk_cup",
    "generic_noodle_mitaimu_bowl",
    "generic_noodle_mianxian_serving",
    "generic_noodle_macaroni_serving",
    "generic_noodle_ramen_serving",
    "generic_noodle_dry_soba_serving",
    "generic_noodle_wet_soba_serving",
    "generic_staple_fried_bantiao_plate",
    "generic_instant_noodle_beef_pack",
    "generic_instant_noodle_shrimp_pack",
    "generic_dumpling_pork_crab_roe_10pc",
    "generic_dumpling_mushroom_chicken_10pc",
    "generic_dumpling_cooked_pork_10pc",
    "generic_wenzhou_wonton_bowl",
    "generic_dim_sum_char_siu_bun_one",
    "generic_dim_sum_white_mantou_one",
    "generic_staple_scallion_pancake_one",
    "generic_staple_chive_pocket_one",
    "generic_snack_red_bean_wrap_cake_one",
}


def test_generic_common_batch_028_loads_tfda_backed_everyday_meals() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "estimable_with_refinement"
        assert record["serving_basis"] == "common_serving"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_file"] == (
            "app/knowledge/tfda_per100g_source_evidence_tw.json"
        )
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_028_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 354
    expected = {
        "generic_noodle_mitaimu_bowl": (302, [210, 420]),
        "generic_instant_noodle_beef_pack": (399, [280, 550]),
        "generic_dumpling_mushroom_chicken_10pc": (324, [230, 455]),
        "generic_staple_scallion_pancake_one": (255, [180, 360]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"

