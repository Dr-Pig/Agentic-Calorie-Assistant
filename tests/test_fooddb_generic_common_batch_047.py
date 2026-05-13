from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_drink_watermelon_juice_300ml",
    "generic_drink_guava_juice_300ml",
    "generic_drink_orange_juice_300ml",
    "generic_drink_cranberry_juice_300ml",
    "generic_drink_tomato_juice_300ml",
    "generic_drink_grass_jelly_honey_cup",
    "generic_drink_aloe_vera_cup",
    "generic_drink_black_bean_tea_500ml",
    "generic_drink_barley_tea_500ml",
    "generic_drink_sarsaparilla_can",
    "generic_drink_sports_drink_500ml",
    "generic_drink_oolong_tea_light_sugar_700ml",
    "generic_snack_square_pastry_serving",
    "generic_snack_wafer_roll_serving",
    "generic_snack_vegetable_soda_cracker_serving",
    "generic_snack_potato_chips_serving",
    "generic_snack_fish_crisp_serving",
    "generic_snack_sachima_one",
    "generic_snack_milk_chocolate_serving",
    "generic_snack_white_sesame_candy_serving",
}


def test_generic_common_batch_047_loads_drink_snack_anchors() -> None:
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


def test_generic_common_batch_047_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 334
    expected = {
        "generic_drink_guava_juice_300ml": (135, [95, 180]),
        "generic_drink_oolong_tea_light_sugar_700ml": (109, [55, 175]),
        "generic_snack_potato_chips_serving": (165, [120, 225]),
        "generic_snack_sachima_one": (242, [175, 325]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
