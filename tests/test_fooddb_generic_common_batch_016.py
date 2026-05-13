from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_staple_white_rice_bowl",
    "generic_noodle_danzai_noodle_bowl",
    "generic_noodle_wenzhou_wonton_bowl",
    "generic_street_meatball_one",
    "generic_street_steamed_shrimp_meatball_one",
    "generic_street_oyster_omelet_plate",
    "generic_staple_fried_ban_tiao_plate",
    "generic_soup_pork_thick_soup_bowl",
    "generic_soup_squid_thick_soup_bowl",
    "generic_breakfast_ham_egg_sandwich_one",
    "generic_breakfast_brown_sugar_mantou_one",
    "generic_dim_sum_char_siu_bun_one",
    "generic_dim_sum_pork_bun_one",
    "generic_dim_sum_vegetable_bun_one",
    "generic_breakfast_chive_pocket_one",
    "generic_staple_black_pepper_ham_pizza_slice",
    "generic_meal_sweet_sour_pork_plate",
    "generic_side_french_fries_serving",
    "generic_side_sweet_potato_fries_serving",
    "generic_dessert_peanut_soup_bowl_tfda",
}


def test_generic_common_batch_016_loads_tfda_dataset_8543_everyday_mains() -> None:
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


def test_generic_common_batch_016_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["generic_staple_white_rice_bowl"]

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 274
    assert item["kcal_point"] == 366
    assert item["kcal_range"] == [300, 450]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
