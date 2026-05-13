from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_breakfast_shaobing_one",
    "generic_snack_hot_dog_2pc",
    "generic_dessert_baked_pudding_cup",
    "generic_dessert_yellow_pudding_cup",
    "generic_drink_grass_jelly_honey_cup",
    "generic_drink_apple_black_tea_cup",
    "generic_drink_sweet_green_tea_cup",
    "generic_drink_yakult_green_tea_cup",
    "generic_drink_two_in_one_coffee_packet",
    "generic_drink_bulk_rice_milk_cup",
    "generic_drink_brown_rice_milk_cup",
    "generic_drink_black_soy_milk_cup",
    "generic_drink_soy_milk_yogurt_cup",
    "generic_dessert_coffee_jelly_cup",
    "generic_snack_yokan_one",
    "generic_snack_salted_peanuts_serving",
    "generic_snack_salted_broad_beans_serving",
    "generic_bakery_pineapple_bun_one",
    "generic_bakery_raisin_custard_bread_one",
    "generic_bakery_croissant_one",
}


def test_generic_common_batch_019_loads_tfda_backed_breakfast_snacks() -> None:
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
        assert record["source_refs"][0]["source_id"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_url"] == "https://data.gov.tw/dataset/8543"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_019_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["generic_bakery_pineapple_bun_one"]

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 400
    assert item["kcal_point"] == 291
    assert item["kcal_range"] == [220, 380]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
