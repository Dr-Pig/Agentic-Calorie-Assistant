from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_snack_green_bean_pastry_one",
    "generic_snack_sun_cake_one",
    "generic_snack_egg_yolk_pastry_one",
    "generic_snack_pineapple_cake_one",
    "generic_snack_sesame_egg_roll_serving",
    "generic_snack_vegetable_soda_crackers_serving",
    "generic_snack_potato_chips_serving",
    "generic_snack_sachima_one",
    "generic_snack_nougat_serving",
    "generic_dessert_tiramisu_slice",
    "generic_dessert_black_forest_cake_slice",
    "generic_staple_pork_blood_rice_cake_one",
    "generic_staple_duck_blood_rice_cake_one",
    "generic_street_coffin_bread_one",
    "generic_street_agei_one",
    "generic_side_frozen_scallion_pancake_one",
    "generic_noodle_soba_wet_bowl",
    "generic_noodle_instant_beef_pack",
    "generic_noodle_instant_shrimp_pack",
    "generic_meat_roast_chicken_serving",
}


def test_generic_common_batch_022_loads_tfda_backed_everyday_dish_records() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "estimable_with_refinement"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_url"] == "https://data.gov.tw/dataset/8543"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"


def test_generic_common_batch_022_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 194
    expected = {
        "generic_snack_pineapple_cake_one": (216, [160, 300]),
        "generic_street_coffin_bread_one": (522, [390, 720]),
        "generic_noodle_instant_beef_pack": (400, [320, 540]),
        "generic_meat_roast_chicken_serving": (350, [260, 470]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
